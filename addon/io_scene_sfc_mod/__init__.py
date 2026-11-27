bl_info = {
    'name': 'Starfleet Command 1/2/OP/3 MOD Import/Export',
    'author': 'SFC MOD project',
    'version': (0, 4, 7),
    'blender': (4, 3, 0),
    'location': 'File > Import',
    'description': 'Import and conservatively export Starfleet Command MOD models (experimental)',
    'category': 'Import-Export',
}

import math
import base64
import json
import os
import re
import struct
import uuid
import zlib
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector
from bpy.props import BoolProperty, EnumProperty, StringProperty, FloatVectorProperty, IntProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .mod_format import inspect, parse_model, group_break_polygons, combine_break_geometry, rewrite_geometry, rewrite_records, texture_stem_collisions, write_chunk, write_geometry, recalculate_normals, update_lod_distances


def from_mod_coordinates(position):
    x, y, z = position
    return (-z, -x, y)


def to_mod_coordinates(position):
    x, y, z = position
    return (-y, z, -x)


def import_rotation():
    return tuple(Matrix(((0., 0., -1.), (-1., 0., 0.), (0., 1., 0.))).to_euler())


def shader_defaults(shader):
    values = {}
    for socket in shader.inputs:
        if not hasattr(socket, 'default_value'):
            continue
        value = socket.default_value
        if isinstance(value, (int, float, bool, str)):
            values[socket.name] = value
        else:
            try:
                values[socket.name] = list(value)
            except TypeError:
                raise ValueError(f'Unsupported shader input: {socket.name}')
    return json.dumps(values, sort_keys=True)


def find_material_shader(material):
    """Find a connected Principled shader without relying on a node's name."""
    if not material or not material.use_nodes:
        return None
    nodes = material.node_tree.nodes
    outputs = [node for node in nodes if node.type == 'OUTPUT_MATERIAL' and node.is_active_output]
    seen = set()
    def trace(node):
        if node.as_pointer() in seen:
            return None
        seen.add(node.as_pointer())
        if node.type == 'BSDF_PRINCIPLED':
            return node
        for socket in node.inputs:
            for link in socket.links:
                result = trace(link.from_node)
                if result:
                    return result
        return None
    for output in outputs:
        result = trace(output)
        if result:
            return result
    return next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)


def mesh_has_faces(context, obj):
    """Check evaluated geometry so empty break objects can be ignored."""
    evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return bool(mesh.polygons)
    finally:
        evaluated.to_mesh_clear()


def point_group_kind(name):
    """Classify the documented hardpoint and damage-point naming conventions."""
    if re.fullmatch(r'hardpoint\d+', name, re.IGNORECASE):
        return 'HardPoints'
    if re.fullmatch(r'[a-f]\d+', name, re.IGNORECASE):
        return 'DamagePoints'
    return None


def is_point_group(collection):
    name = re.sub(r'\.\d{3}$', '', collection.name).casefold()
    return name in ('hardpoints', 'damagepoints')


def model_point_objects(collection):
    """Find direct and grouped points once, preserving imported point order."""
    objects = list(collection.objects)
    for child in collection.children:
        if is_point_group(child):
            objects.extend(child.objects)
    seen, points = set(), []
    for obj in objects:
        if obj.type == 'EMPTY' and obj.as_pointer() not in seen:
            seen.add(obj.as_pointer())
            points.append(obj)
    return sorted(points, key=lambda obj: (0, int(obj['mod_point_index'])) if 'mod_point_index' in obj else (1, 0))


def model_collection_for_object(context, obj):
    collections = [c for c in obj.users_collection if c != context.scene.collection]
    for collection in collections:
        if is_point_group(collection):
            parents = [c for c in [context.scene.collection, *bpy.data.collections]
                       if collection.name in c.children]
            if parents:
                return parents[0]
        else:
            return collection
    return context.scene.collection


def apply_imported_normals(mesh, polygons, materials):
    """Restore MOD corner-normal directions for Blender shading without welding."""
    normals = [(0., 0., 0.)] * len(mesh.loops)
    edge_sides = {}
    for face, polygon in zip(mesh.polygons, polygons):
        flags = materials[polygon['material']]['flags']
        face.use_smooth = not (flags & 0x04 and not flags & 0x02)
        loops = list(face.loop_indices)
        for loop_index, corner_index in zip(loops, (1, 0, 2)):
            normal = struct.unpack_from('<3f', polygon['corners'][corner_index]['raw'], 4)
            normals[loop_index] = normal if all(math.isfinite(value) for value in normal) else (0., 0., 0.)
        if face.use_smooth:
            for index, loop_index in enumerate(loops):
                next_index = loops[(index + 1) % len(loops)]
                loop, following = mesh.loops[loop_index], mesh.loops[next_index]
                edge_sides.setdefault(loop.edge_index, []).append({loop.vertex_index: Vector(normals[loop_index]),
                                                                   following.vertex_index: Vector(normals[next_index])})
    for index, sides in edge_sides.items():
        if len(sides) != 2:
            continue
        for vertex, first in sides[0].items():
            second = sides[1].get(vertex)
            if second is not None and first.length_squared > 1e-20 and second.length_squared > 1e-20:
                if (first.normalized() - second.normalized()).length_squared > 1e-10:
                    mesh.edges[index].use_edge_sharp = True
                    break
    if normals:
        mesh.normals_split_custom_set(normals)
        mesh['mod_imported_normals'] = True
    mesh.update()


def import_model(context, filepath, import_smoothing=True):
    path = Path(filepath)
    is_break = path.stem.casefold().endswith('_brk')
    source_bytes = path.read_bytes()
    model = parse_model(source_bytes)
    if is_break and len(model['meshes']) != 1:
        raise ValueError('Break model must contain one geometry chunk')
    groups = group_break_polygons(model['meshes'][0]) if is_break else None
    pivots = {}
    if is_break:
        for point in model['points']:
            match = re.search(r'(\d+)pivot$', point['name'], re.IGNORECASE)
            if match:
                key = int(match.group(1)) - 1
                if key in pivots:
                    raise ValueError('Duplicate numbered break pivot')
                pivots[key] = point
    available = [p for p in path.parent.iterdir() if p.is_file()]
    warnings = []
    collection = bpy.data.collections.new(f'SFC MOD: {path.stem}')
    context.scene.collection.children.link(collection)
    collection['mod_source_zlib_base64'] = base64.b64encode(zlib.compress(source_bytes)).decode('ascii')
    collection['mod_source_filename'] = path.name
    materials = []
    def texture(reference):
        filename = reference.replace('\\', '/').rsplit('/', 1)[-1]
        exact = [p for p in available if p.name.casefold() == filename.casefold()]
        candidates = exact if exact else [p for p in available if p.stem.casefold() == filename.casefold() and p.suffix.casefold() in bpy.path.extensions_image]
        if len(candidates) != 1:
            warnings.append(f'{"Ambiguous" if candidates else "Missing"} texture: {reference}')
            return None
        try:
            return bpy.data.images.load(str(candidates[0]), check_existing=True)
        except (RuntimeError, OSError) as exc:
            warnings.append(f'Could not load texture {reference}: {exc}')
            return None
    try:
        for index, source in enumerate(model['materials']):
            mat = bpy.data.materials.new(f'{path.stem} Material {index:02d}')
            materials.append(mat)
            mat['mod_flags'] = source['flags']
            mat['mod_record_hex'] = source['raw'].hex()
            mat.use_nodes = True
            shader = mat.node_tree.nodes.get('Principled BSDF')
            diffuse = None
            if source['diffuse']:
                mat['mod_diffuse_stem'] = source['diffuse']
                image = texture(source['diffuse'])
                mat['mod_diffuse_loaded'] = bool(image)
                if image:
                    diffuse = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    diffuse.label = 'MOD diffuse map'
                    diffuse.image = image
                    mat.node_tree.links.new(diffuse.outputs['Color'], shader.inputs['Base Color'])
            if source['illumination']:
                mat['mod_illumination_stem'] = source['illumination']
                image = texture(source['illumination'])
                mat['mod_illumination_loaded'] = bool(image)
                if image:
                    image.colorspace_settings.name = 'Non-Color'
                    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    node.label = 'OP illumination map'
                    node.image = image
                    if diffuse:
                        mix = mat.node_tree.nodes.new('ShaderNodeMixRGB')
                        mix.blend_type = 'MULTIPLY'
                        mix.inputs[0].default_value = 1.0
                        mat.node_tree.links.new(diffuse.outputs['Color'], mix.inputs[1])
                        mat.node_tree.links.new(node.outputs['Color'], mix.inputs[2])
                        mat.node_tree.links.new(mix.outputs['Color'], shader.inputs['Emission Color'])
                        shader.inputs['Emission Strength'].default_value = 1.0
            mat['mod_shader_defaults'] = shader_defaults(shader)
        if is_break:
            source = model['meshes'][0]
            parts = [(group + 1, {'vertices': source['vertices'], 'polygons': polys}, pivots.get(group))
                     for group, polys in sorted(groups.items())]
        else:
            parts = [(number, source, None) for number, source in enumerate(model['meshes'], 1)]
        for number, source, pivot in parts:
            name = f'{path.stem}_{number}'
            mesh = bpy.data.meshes.new(name)
            mesh['mod_polygon_records'] = json.dumps([
                (p['raw_header'] + b''.join(c['raw'] for c in p['corners'])).hex()
                for p in source['polygons']
            ])
            used = sorted({c['index'] for p in source['polygons'] for c in p['corners']}) if is_break else list(range(len(source['vertices'])))
            remap = {old: new for new, old in enumerate(used)}
            origin = Vector(pivot['position']) if pivot else Vector((0, 0, 0))
            faces = [[remap[p['corners'][i]['index']] for i in (1, 0, 2)] for p in source['polygons']]
            vertices = [Vector(source['vertices'][i]) - origin for i in used]
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            uv = mesh.uv_layers.new(name='MOD UV')
            for mat in materials:
                mesh.materials.append(mat)
            for face, poly in zip(mesh.polygons, source['polygons']):
                face.material_index = poly['material']
                for loop, i in zip(face.loop_indices, (1, 0, 2)):
                    uv.data[loop].uv = poly['corners'][i]['uv']
            if import_smoothing:
                apply_imported_normals(mesh, source['polygons'], model['materials'])
            else:
                for face in mesh.polygons:
                    face.use_smooth = False
            obj = bpy.data.objects.new(mesh.name, mesh)
            collection.objects.link(obj)
            obj.rotation_euler = import_rotation()
            obj.location = from_mod_coordinates(origin)
            if is_break:
                obj['mod_piece_id'] = number - 1
                obj['mod_vertex_indices'] = used
                if pivot:
                    obj['mod_pivot_name'] = pivot['name']
                    obj['mod_pivot_position'] = pivot['position']
            else:
                obj['mod_lod_index'] = number - 1
                obj.hide_set(number != 1)
        point_groups = {}
        for point_index, point in enumerate(model['points']):
            obj = bpy.data.objects.new(point['name'], None)
            group_name = point_group_kind(point['name'])
            if group_name:
                if group_name not in point_groups:
                    point_groups[group_name] = bpy.data.collections.new(group_name)
                    collection.children.link(point_groups[group_name])
                point_groups[group_name].objects.link(obj)
            else:
                collection.objects.link(obj)
            obj.location = from_mod_coordinates(point['position'])
            obj.empty_display_type = 'SPHERE'
            obj.empty_display_size = 0.15
            obj['mod_name'] = point['name']
            obj['mod_point_index'] = point_index
            obj['mod_initial_blender_name'] = obj.name
            obj['mod_position'] = point['position']
            obj['mod_string_offset'] = point['name_offset']
    except Exception:
        for obj in list(collection.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(collection.children):
            bpy.data.collections.remove(child)
        bpy.data.collections.remove(collection)
        raise
    return warnings


def prepare_standard_export(collection, destination, split_angle=None, direct_normals=False):
    return prepare_imported_export(bpy.context, collection, destination, break_mode=False, split_angle=split_angle, direct_normals=direct_normals)


class IMPORT_OT_sfc_mod(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.sfc_mod'
    bl_label = 'Import SFC 1/2/OP/3 MOD'
    filename_ext = '.mod'
    filter_glob: StringProperty(default='*.mod;*.MOD', options={'HIDDEN'})
    import_smoothing: BoolProperty(
        name='Import Smoothing',
        description='Apply the model’s stored normals to Blender shading; turn off for flat faces',
        default=True,
    )

    def draw(self, context):
        self.layout.prop(self, 'import_smoothing')

    def execute(self, context):
        try:
            warnings = import_model(context, self.filepath, import_smoothing=self.import_smoothing)
        except Exception as exc:
            self.report({'ERROR'}, f'MOD import failed: {exc}')
            return {'CANCELLED'}
        if warnings:
            self.report({'WARNING'}, f'{len(warnings)} import warning(s): {warnings[0]}')
        return {'FINISHED'}


def prepare_new_mesh_export(context, obj, destination, break_mode=False, split_angle=None, direct_normals=False):
    """Build a MOD from a selected authored mesh and its model collection."""
    match = re.fullmatch(r'(.+)_(\d+)', obj.name)
    candidates = [c for c in obj.users_collection if c != context.scene.collection]
    collection = candidates[0] if candidates else context.scene.collection
    meshes = [obj]
    skipped_empty = []
    if break_mode:
        selected_name = re.fullmatch(r'(.+)_brk_\d+', obj.name, re.IGNORECASE)
        prefix = selected_name.group(1).casefold() if selected_name else None
        meshes = []
        for candidate in collection.objects:
            name = re.fullmatch(r'(.+)_brk_\d+', candidate.name, re.IGNORECASE)
            if candidate.type == 'MESH' and name and name.group(1).casefold() == prefix:
                if mesh_has_faces(context, candidate):
                    meshes.append(candidate)
                else:
                    skipped_empty.append(candidate.name)
        if not meshes:
            raise ValueError('No named break pieces found in model collection')
    elif match:
        prefix = match.group(1).casefold()
        named = []
        for candidate in collection.objects:
            other = re.fullmatch(r'(.+)_(\d+)', candidate.name)
            if candidate.type == 'MESH' and other and other.group(1).casefold() == prefix:
                named.append((int(other.group(2)), candidate))
        meshes = [candidate for _, candidate in sorted(named, key=lambda item: item[0])]
    points = model_point_objects(collection)
    strings = bytearray(b'\0')
    material_records = []
    material_lookup = {}
    warnings = [f'Skipped empty break piece: {name}' for name in skipped_empty]
    geometries = []
    radius = 0.0

    def string_offset(value):
        offset = len(strings)
        strings.extend(value.encode('ascii') + b'\0')
        return offset

    def image_in_socket(socket, seen=None, exclude=None):
        seen = seen or set()
        for link in socket.links:
            node = link.from_node
            if node.as_pointer() in seen:
                continue
            seen.add(node.as_pointer())
            if node.type == 'TEX_IMAGE' and node.image and node.image != exclude:
                return node.image
            for child in node.inputs:
                found = image_in_socket(child, seen, exclude)
                if found:
                    return found
        return None

    def image_offset(image):
        if not image:
            return None
        if not image.filepath:
            warnings.append(f'Texture {image.name} has no file path and cannot be referenced')
            return None
        path = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
        if os.path.normcase(str(path.parent)) != os.path.normcase(str(Path(destination).resolve().parent)):
            warnings.append(f'Texture is outside save directory: {path}')
        return string_offset(path.stem)

    def material_index(mat):
        key = mat.as_pointer() if mat else None
        if key in material_lookup:
            return material_lookup[key]
        diffuse = illumination = None
        if mat and mat.use_nodes:
            shader = find_material_shader(mat)
            if shader:
                diffuse = image_in_socket(shader.inputs['Base Color'])
                illumination = image_in_socket(shader.inputs['Emission Color'], exclude=diffuse)
                if illumination is None:
                    illumination = image_in_socket(shader.inputs['Emission Color'])
        diffuse_offset = image_offset(diffuse)
        illumination_offset = image_offset(illumination)
        flags = (1 if diffuse_offset is not None else 0) | (0x20 if illumination_offset is not None else 0)
        raw = struct.pack('<II2fIII', flags, 0x00ffffff, 1., 1., 0, 0, diffuse_offset or 0)
        if illumination_offset is not None:
            raw += struct.pack('<II', 0, illumination_offset)
        material_lookup[key] = len(material_records)
        material_records.append(raw)
        return material_lookup[key]

    for mesh_obj in meshes:
        geometry = authored_geometry(context, mesh_obj, material_index, split_angle=split_angle, direct_normals=direct_normals)
        if break_mode:
            name_match = re.fullmatch(r'.+_brk_(\d+)', mesh_obj.name, re.IGNORECASE)
            piece_id = int(mesh_obj['mod_piece_id']) if 'mod_piece_id' in mesh_obj else int(name_match.group(1)) - 1
            geometries.append((piece_id, geometry))
        else:
            geometries.append(geometry)
        radius = max(radius, max((math.sqrt(sum(v*v for v in p)) for p in geometry['vertices']), default=0.0))
    if break_mode:
        geometries = [combine_break_geometry(sorted(geometries, key=lambda item: item[0]))]
    point_data = bytearray()
    for point in points:
        p = point.matrix_world.translation
        point_data.extend(struct.pack('<3fI', *to_mod_coordinates(p), string_offset(point.name)))
    header = struct.pack('<IfI6f', 0x200, radius, len(geometries), 5., 0., 100., 200., 300., 400.)
    body = header + write_chunk(b'STRS', strings) + write_chunk(b'PNTS', point_data) + write_chunk(b'MATS', b''.join(material_records))
    body += b''.join(write_chunk(b'MOD0', write_geometry(geometry)) for geometry in geometries)
    return b'MDLS' + struct.pack('<I', len(body)) + body, list(dict.fromkeys(warnings))


def prepare_break_export(context, collection, destination, split_angle=None, direct_normals=False):
    return prepare_imported_export(context, collection, destination, break_mode=True, split_angle=split_angle, direct_normals=direct_normals)


def prepare_imported_export(context, collection, destination, break_mode, split_angle=None, direct_normals=False):
    """Write current imported geometry, materials, textures and point empties."""
    key = 'mod_piece_id' if break_mode else 'mod_lod_index'
    stem = Path(collection.get('mod_source_filename', '')).stem
    pattern = re.compile(re.escape(stem) + r'_(\d+)$', re.IGNORECASE)
    numbered = []
    used = set()
    skipped_empty = []
    id_counts = {}
    for obj in collection.objects:
        if obj.type == 'MESH' and key in obj and (not break_mode or mesh_has_faces(context, obj)):
            number = int(obj[key])
            id_counts[number] = id_counts.get(number, 0) + 1
    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        match = pattern.fullmatch(obj.name)
        if key not in obj and not match:
            continue
        if break_mode and not mesh_has_faces(context, obj):
            skipped_empty.append(obj.name)
            continue
        index = int(obj[key]) if key in obj else int(match.group(1)) - 1
        source_index = int(obj[key]) if key in obj else None
        if match and source_index is not None and id_counts[source_index] > 1 and int(match.group(1)) - 1 != source_index:
            index = int(match.group(1)) - 1
            source_index = None
        if index in used and match:
            index = int(match.group(1)) - 1
            source_index = None
        if index in used or index < 0:
            raise ValueError(f'Duplicate or invalid model number: {obj.name}')
        used.add(index)
        numbered.append((index, obj, source_index))
    numbered.sort(key=lambda item: item[0])
    pieces = [item[1] for item in numbered]
    if not pieces:
        raise ValueError('No imported model meshes found')
    source = zlib.decompress(base64.b64decode(collection['mod_source_zlib_base64'], validate=True))
    model = parse_model(source)
    context.view_layer.update()
    chunks = inspect(source)
    strings_chunk = next((source[o + 8:o + 8 + n] for tag, o, n in chunks if tag == b'STRS'), b'')
    strings = bytearray(strings_chunk)
    materials = []
    for piece in pieces:
        for material in (list(piece.data.materials) or [None]):
            if not any(existing == material for existing in materials):
                materials.append(material)
    warnings = [f'Skipped empty break piece: {name}' for name in skipped_empty]
    image_paths = []
    def add_string(value):
        offset = len(strings)
        strings.extend(value.encode('ascii') + b'\0')
        return offset

    def string_matches(offset, value):
        if offset is None or not 0 <= offset < len(strings_chunk):
            return False
        end = strings_chunk.find(b'\0', offset)
        return end >= 0 and strings_chunk[offset:end] == value.encode('ascii')

    def find_image(socket, excluded=None, seen=None):
        seen = seen if seen is not None else set()
        for link in socket.links:
            node = link.from_node
            if node.as_pointer() in seen:
                continue
            seen.add(node.as_pointer())
            if node.type == 'TEX_IMAGE' and node.image and node.image != excluded:
                return node.image
            for child in node.inputs:
                found = find_image(child, excluded, seen)
                if found:
                    return found
        return None

    material_data = bytearray()
    for mat in materials:
        old_raw = bytes.fromhex(mat.get('mod_record_hex', '')) if mat else b''
        raw = bytearray(old_raw[:28] if len(old_raw) >= 28 else struct.pack('<II2fIII', 0, 0x00ffffff, 1., 1., 0, 0, 0))
        old_flags = struct.unpack_from('<I', raw)[0]
        flags = old_flags & ~0x21
        shader = find_material_shader(mat)
        if shader and mat.get('mod_shader_defaults') and mat.get('mod_shader_defaults') != shader_defaults(shader):
            warnings.append(f'Some shader settings in {mat.name} are not encoded')
        diffuse = find_image(shader.inputs['Base Color']) if shader else None
        illum = find_image(shader.inputs['Emission Color'], diffuse) if shader else None
        if illum is None and shader and not old_raw:
            illum = find_image(shader.inputs['Emission Color'])
        if mat and mat.use_nodes and illum is None:
            illum_node = next((n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.label == 'OP illumination map'), None)
            illum = illum_node.image if illum_node else None
        refs = []
        for field, image, flag, offset in (('diffuse', diffuse, 1, 24), ('illumination', illum, 0x20, 32)):
            old_stem = mat.get('mod_' + field + '_stem') if mat else None
            loaded = mat.get('mod_' + field + '_loaded', False) if mat else False
            if image and not image.filepath:
                warnings.append(f'Texture {image.name} has no file path and cannot be referenced')
                stem = old_stem
            elif image and image.filepath:
                image_path = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
                image_paths.append(str(image_path))
                stem = image_path.stem
                if old_stem and stem.casefold() == old_stem.casefold():
                    stem = old_stem
                if os.path.normcase(str(image_path.parent)) != os.path.normcase(str(Path(destination).resolve().parent)):
                    warnings.append(f'Texture is outside save directory: {image_path}')
            else:
                stem = old_stem if old_stem and not loaded else None
            if stem is not None:
                flags |= flag
                old_offset = struct.unpack_from('<I', old_raw, offset)[0] if old_flags & flag and len(old_raw) >= offset + 4 else None
                if old_stem == stem and string_matches(old_offset, stem):
                    refs.append(old_offset)
                else:
                    refs.append(add_string(stem))
            else:
                refs.append(0)
        struct.pack_into('<I', raw, 0, flags)
        struct.pack_into('<I', raw, 24, refs[0])
        if flags & 0x20:
            raw.extend(old_raw[28:36] if len(old_raw) >= 36 else bytes(8))
            struct.pack_into('<I', raw, 32, refs[1])
        material_data.extend(raw)
    collisions = texture_stem_collisions(image_paths)
    if collisions:
        warnings.append('Different images share a MOD texture stem: ' + ', '.join(sorted(collisions)))
    def material_index(mat):
        for index, candidate in enumerate(materials):
            if candidate == mat or (candidate and mat and candidate.original == mat.original):
                return index
        raise ValueError('Mesh uses a material outside its slots')
    if break_mode:
        geometries = [(number, authored_geometry(context, obj, material_index, split_angle=split_angle, direct_normals=direct_normals)) for number, obj, _ in numbered]
        geometries = [combine_break_geometry(geometries)]
        if direct_normals:
            geometries[0]['_normals_supplied'] = True
    else:
        geometries = []
        for _, obj, source_index in numbered:
            mesh = obj.data
            if len(mesh.vertices) > 65536:
                raise ValueError('Mesh exceeds the MOD vertex index limit')
            if split_angle != 'BLENDER' and not direct_normals and not mesh.get('mod_imported_normals') and (mesh.has_custom_normals or any(edge.use_edge_sharp for edge in mesh.edges) or any(face.use_smooth for face in mesh.polygons)):
                warnings.append(f'Blender smoothing settings on {obj.name} are not encoded')
            expected_rotation = import_rotation()
            evaluated = (direct_normals or split_angle is not None or source_index is None or source_index >= len(model['meshes']) or obj.parent or obj.constraints or obj.modifiers or mesh.shape_keys or
                    obj.rotation_mode != 'XYZ' or tuple(obj.location) != (0.0, 0.0, 0.0) or
                    tuple(obj.rotation_euler) != expected_rotation or tuple(obj.scale) != (1.0, 1.0, 1.0) or
                    tuple(obj.delta_location) != (0.0, 0.0, 0.0) or tuple(obj.delta_rotation_euler) != (0.0, 0.0, 0.0) or
                    tuple(obj.delta_scale) != (1.0, 1.0, 1.0))
            if evaluated:
                geometry = authored_geometry(context, obj, material_index, split_angle=split_angle, direct_normals=direct_normals)
                geometry['_source_index'] = source_index if source_index is not None and source_index < len(model['meshes']) else None
                geometries.append(geometry)
                continue
            original = model['meshes'][source_index]
            original['_source_index'] = source_index
            geometries.append(original)
            original['vertices'] = [tuple(vertex.co) for vertex in mesh.vertices]
            changed = (len(mesh.polygons) != len(original['polygons']) or
                       any(len(face.vertices) != 3 or tuple(face.vertices) != tuple(poly['corners'][i]['index'] for i in (1, 0, 2))
                           for face, poly in zip(mesh.polygons, original['polygons'])))
            local_mats = list(mesh.materials) or [None]
            if changed:
                mesh.calc_loop_triangles()
                polygons = []
                for tri in mesh.loop_triangles:
                    corners = []
                    for loop in (tri.loops[1], tri.loops[0], tri.loops[2]):
                        index = mesh.loops[loop].vertex_index
                        uv = tuple(mesh.uv_layers.active.data[loop].uv) if mesh.uv_layers.active else (0., 0.)
                        raw = struct.pack('<I3f2fI', index, 0., 0., 0., *uv, 0)
                        corners.append({'index': index, 'uv': uv, 'raw': raw})
                    index = material_index(local_mats[tri.material_index])
                    polygons.append({'material': index, 'raw_header': struct.pack('<II3f', 3, index, 0., 0., 0.), 'corners': corners})
                original['polygons'] = polygons
            else:
                for face, polygon in zip(mesh.polygons, original['polygons']):
                    polygon['material'] = material_index(local_mats[face.material_index])
                    for loop, corner_index in zip(face.loop_indices, (1, 0, 2)):
                        polygon['corners'][corner_index]['uv'] = tuple(mesh.uv_layers.active.data[loop].uv) if mesh.uv_layers.active else (0., 0.)
    point_data = bytearray()
    for obj in model_point_objects(collection):
        position = obj.matrix_world.translation
        name = obj.get('mod_name', obj.name) if obj.name == obj.get('mod_initial_blender_name') else obj.name
        offset = obj.get('mod_string_offset') if name == obj.get('mod_name') else None
        if not string_matches(offset, name):
            offset = add_string(name)
        point_data.extend(struct.pack('<3fI', *to_mod_coordinates(position), offset))
    geometry_data = rewrite_geometry(source, geometries)
    replacements = {b'STRS': bytes(strings), b'PNTS': bytes(point_data), b'MATS': bytes(material_data)}
    body = bytearray(geometry_data[8:44])
    seen = set()
    source_has_points = any(tag == b'PNTS' for tag, _, _ in inspect(geometry_data))
    for tag, offset, size in inspect(geometry_data):
        end = offset + 8 + size
        if tag == b'MATS' and not source_has_points and point_data:
            body.extend(write_chunk(b'PNTS', point_data))
            seen.add(b'PNTS')
        if tag in replacements:
            body.extend(write_chunk(tag, replacements[tag]))
            seen.add(tag)
        else:
            body.extend(geometry_data[offset:(end + 3) & ~3])
    if b'PNTS' not in seen and point_data:
        body.extend(write_chunk(b'PNTS', point_data))
    return b'MDLS' + struct.pack('<I', len(body)) + body, list(dict.fromkeys(warnings))


def authored_geometry(context, obj, material_index, split_angle=None, direct_normals=False):
    """Convert one evaluated Blender mesh to an SFC geometry record."""
    evaluated = obj.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    split_mesh = None
    try:
        if split_angle is not None:
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                bm.normal_update()
                if split_angle == 'BLENDER':
                    sides = {}
                    normals = mesh.corner_normals
                    for face in mesh.polygons:
                        loops = list(face.loop_indices)
                        for i, loop_index in enumerate(loops):
                            next_index = loops[(i + 1) % len(loops)]
                            loop, following = mesh.loops[loop_index], mesh.loops[next_index]
                            sides.setdefault(loop.edge_index, []).append({loop.vertex_index: normals[loop_index].vector.copy(),
                                                                        following.vertex_index: normals[next_index].vector.copy()})
                    bm.edges.ensure_lookup_table()
                    edges = []
                    for index, edge in enumerate(mesh.edges):
                        adjacent = sides.get(index, [])
                        if len(adjacent) != 2 or not bm.edges[index].is_manifold:
                            continue
                        if edge.use_edge_sharp or any((adjacent[0][vertex] - adjacent[1][vertex]).length_squared > 1e-10
                                                     for vertex in edge.vertices):
                            edges.append(bm.edges[index])
                else:
                    edges = [edge for edge in bm.edges if edge.is_manifold and edge.calc_face_angle(0.0) > split_angle]
                if edges:
                    bmesh.ops.split_edges(bm, edges=edges)
                split_mesh = bpy.data.meshes.new('SFC export temporary mesh')
                for material in mesh.materials:
                    split_mesh.materials.append(material)
                bm.to_mesh(split_mesh)
            finally:
                bm.free()
            mesh = split_mesh
        mesh.calc_loop_triangles()
        if len(mesh.vertices) > 65536:
            raise ValueError('Mesh exceeds the MOD vertex index limit')
        vertices = []
        for vertex in mesh.vertices:
            p = evaluated.matrix_world @ vertex.co
            vertices.append(to_mod_coordinates(p))
        material_indices = [material_index(mat) for mat in (list(mesh.materials) or [None])]
        polygons = []
        normal_matrix = evaluated.matrix_world.to_3x3().inverted_safe().transposed() if direct_normals else None
        corner_normals = mesh.corner_normals if direct_normals else None
        supplied_normals = []
        mirrored = direct_normals and evaluated.matrix_world.to_3x3().determinant() < 0.0
        uv = mesh.uv_layers.active
        for tri in mesh.loop_triangles:
            corners = []
            face_normals = []
            ordered_loops = (tri.loops[0], tri.loops[1], tri.loops[2]) if mirrored else (tri.loops[1], tri.loops[0], tri.loops[2])
            for loop_id in ordered_loops:
                index = mesh.loops[loop_id].vertex_index
                coords = tuple(uv.data[loop_id].uv) if uv else (0., 0.)
                raw = struct.pack('<I3f2fI', index, 0., 0., 0., *coords, 0)
                corners.append({'index': index, 'uv': coords, 'raw': raw})
                if direct_normals:
                    normal = normal_matrix @ corner_normals[loop_id].vector
                    if normal.length_squared:
                        normal.normalize()
                    face_normals.append(to_mod_coordinates(normal))
            index = material_indices[tri.material_index]
            polygons.append({'material': index, 'raw_header': struct.pack('<II3f', 3, index, 0., 0., 0.), 'corners': corners})
            if direct_normals:
                supplied_normals.append(face_normals)
        geometry = {'vertices': vertices, 'polygons': polygons, 'unknown': []}
        recalculate_normals(geometry)
        if direct_normals:
            for polygon, normals in zip(polygons, supplied_normals):
                for corner, normal in zip(polygon['corners'], normals):
                    raw = bytearray(corner['raw'])
                    struct.pack_into('<3f', raw, 4, *normal)
                    corner['raw'] = bytes(raw)
            geometry['_normals_supplied'] = True
        return geometry
    finally:
        evaluated.to_mesh_clear()
        if split_mesh is not None:
            bpy.data.meshes.remove(split_mesh)


def open_export_temp(directory):
    """Create an exclusive temporary output without retrying access errors."""
    for _ in range(10):
        path = Path(directory) / ('.sfc-mod-' + uuid.uuid4().hex)
        try:
            return path, open(path, 'xb')
        except FileExistsError:
            continue
    raise FileExistsError('Could not find an available temporary output name')


def output_paths(path, mode, has_standard, has_break):
    """Determine distinct standard and break destinations before writing."""
    path = Path(path)
    stem = path.stem[:-4] if path.stem.casefold().endswith('_brk') else path.stem
    outputs = {}
    if mode in ('AUTO', 'STANDARD') and has_standard:
        outputs['standard'] = path.with_name(stem + '.mod')
    if mode in ('AUTO', 'BREAK') and has_break:
        outputs['break'] = path.with_name(stem + '_brk.mod')
    if not outputs:
        raise ValueError('No model objects found for the chosen export mode')
    return outputs


def find_export_models(context, active):
    """Find standard and break objects belonging to the selected ship."""
    if not active:
        raise ValueError('Select a model object to export')
    collection = model_collection_for_object(context, active)
    source_name = collection.get('mod_source_filename', '')
    choices = {}
    if source_name:
        stem = Path(source_name).stem
        base = stem[:-4] if stem.casefold().endswith('_brk') else stem
        for candidate in bpy.data.collections:
            filename = candidate.get('mod_source_filename', '')
            if not filename:
                continue
            part = Path(filename).stem
            kind = 'break' if part.casefold().endswith('_brk') else 'standard'
            prefix = part[:-4] if kind == 'break' else part
            if prefix.casefold() != base.casefold():
                continue
            objects = [o for o in candidate.objects if o.type == 'MESH']
            if kind == 'break':
                present = []
                for obj in objects:
                    if mesh_has_faces(context, obj):
                        present.append(obj)
                    else:
                        choices.setdefault('_skipped_break', []).append(obj.name)
                objects = present
            if objects:
                if kind in choices and choices[kind][0] != candidate:
                    raise ValueError(f'Multiple imported {kind} collections match {base}')
                choices[kind] = (candidate, objects[0])
        return choices
    if active.type == 'EMPTY':
        meshes = [obj for obj in collection.objects if obj.type == 'MESH']
        bases = {m.group(1).casefold() for obj in meshes
                 if (m := re.fullmatch(r'(.+?)(?:_brk)?_\d+', obj.name, re.IGNORECASE))}
        if len(bases) == 1:
            active = next(obj for obj in meshes if re.fullmatch(r'(.+?)(?:_brk)?_\d+', obj.name, re.IGNORECASE))
        elif len(meshes) == 1:
            active = meshes[0]
        else:
            raise ValueError('Select a model mesh to identify which model to export')
    match = re.fullmatch(r'(.+?)(?:_brk)?_\d+', active.name, re.IGNORECASE)
    base = match.group(1).casefold() if match else active.name.casefold()
    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        break_match = re.fullmatch(r'(.+)_brk_\d+', obj.name, re.IGNORECASE)
        lod_match = re.fullmatch(r'(.+)_\d+', obj.name, re.IGNORECASE)
        if break_match and break_match.group(1).casefold() == base:
            if mesh_has_faces(context, obj):
                choices.setdefault('break', (collection, obj))
            else:
                choices.setdefault('_skipped_break', []).append(obj.name)
        elif lod_match and lod_match.group(1).casefold() == base:
            choices.setdefault('standard', (collection, obj))
    if not match and active.type == 'MESH':
        choices['standard'] = (collection, active)
    return choices


def destination_snapshot(path):
    try:
        stat = Path(path).stat()
        return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
    except FileNotFoundError:
        return None


def write_export_outputs(outputs, snapshots):
    """Stage selected outputs and replace only destinations that were confirmed."""
    staged = {}
    try:
        for path in outputs:
            if destination_snapshot(path) != snapshots[str(path)]:
                raise ValueError(f'Output changed since confirmation: {path}')
        for path, data in outputs.items():
            temp_path, stream = open_export_temp(path.parent)
            staged[path] = temp_path
            with stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        for path, temp_path in staged.items():
            if destination_snapshot(path) != snapshots[str(path)]:
                raise ValueError(f'Output changed since confirmation: {path}')
            if snapshots[str(path)] is None:
                if os.name == 'nt':
                    os.rename(temp_path, path)
                else:
                    os.link(temp_path, path)
                    temp_path.unlink()
            else:
                os.replace(temp_path, path)
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def prepare_selected_outputs(context, active, paths, include_empty_break_warnings=False, split_angle=None, direct_normals=False):
    choices = find_export_models(context, active)
    outputs, warnings = {}, []
    if include_empty_break_warnings and 'break' not in choices:
        warnings.extend(f'Skipped empty break piece: {name}' for name in choices.get('_skipped_break', []))
    for kind, path in paths.items():
        if kind not in choices:
            raise ValueError(f'The selected model no longer contains a {kind} model')
        collection, obj = choices[kind]
        if collection.get('mod_source_zlib_base64'):
            data, notes = (prepare_break_export(context, collection, path, split_angle=split_angle, direct_normals=direct_normals) if kind == 'break'
                           else prepare_standard_export(collection, path, split_angle=split_angle, direct_normals=direct_normals))
        else:
            data, notes = prepare_new_mesh_export(context, obj, path, break_mode=(kind == 'break'), split_angle=split_angle, direct_normals=direct_normals)
        outputs[path] = data
        warnings.extend(notes)
    return outputs, list(dict.fromkeys(warnings))


def report_export_warnings(operator, warnings):
    if warnings:
        detail = bpy.data.texts.new('SFC MOD Export Warnings')
        detail.write('\n'.join(warnings))
        skipped = [warning for warning in warnings if warning.startswith('Skipped empty break piece:')]
        if len(skipped) == 1:
            message = skipped[0]
            if len(warnings) > 1:
                message += f'; see Text Editor: {detail.name}'
        elif skipped:
            message = f'Skipped {len(skipped)} empty break pieces. See Text Editor: {detail.name}'
        else:
            message = f'{len(warnings)} export warning(s). See Text Editor: {detail.name}'
        operator.report({'WARNING'}, message)


def initial_lod_settings(context, active):
    """Read the distances that would be exported before opening the file browser."""
    choices = find_export_models(context, active)
    if 'standard' not in choices:
        return 0, (0., 100., 200., 300., 400.)
    preview_path = Path(bpy.path.abspath('//')) / '__sfc_lod_preview__.mod'
    outputs, _ = prepare_selected_outputs(context, active, {'standard': preview_path})
    standard = outputs[preview_path]
    return struct.unpack_from('<I', standard, 16)[0], struct.unpack_from('<5f', standard, 24)


class EXPORT_OT_sfc_mod_confirm(bpy.types.Operator):
    bl_idname = 'export_scene.sfc_mod_confirm'
    bl_label = 'Confirm MOD Overwrite'
    payload: StringProperty(options={'HIDDEN'})
    overwrite_standard: BoolProperty(name='Overwrite standard model', default=True)
    overwrite_break: BoolProperty(name='Overwrite break model', default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        state = json.loads(self.payload)
        self.layout.label(text='Select existing files to overwrite:')
        for kind, name in state['paths'].items():
            if state['snapshots'][name] is not None:
                self.layout.prop(self, 'overwrite_' + kind, text='Overwrite ' + Path(name).name)

    def execute(self, context):
        try:
            state = json.loads(self.payload)
            active = bpy.data.objects.get(state['active'])
            paths = {kind: Path(name) for kind, name in state['paths'].items()
                     if state['snapshots'][name] is None or getattr(self, 'overwrite_' + kind)}
            if not paths:
                self.report({'INFO'}, 'No files selected for export')
                return {'CANCELLED'}
            smoothing = state.get('smoothing_mode', 'KEEP')
            outputs, warnings = prepare_selected_outputs(context, active, paths, state.get('include_empty_break_warnings', False),
                                                       split_angle='BLENDER' if smoothing == 'SPLIT' else None,
                                                       direct_normals=smoothing == 'DIRECT')
            if state.get('has_distances', False) and 'standard' in paths:
                path = paths['standard']
                outputs[path] = update_lod_distances(outputs[path], distances=state['distances'])
            write_export_outputs(outputs, state['snapshots'])
            report_export_warnings(self, warnings)
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f'MOD export failed: {exc}')
            return {'CANCELLED'}


class EXPORT_OT_sfc_mod(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.sfc_mod'
    bl_label = 'Export SFC 1/2/OP/3 MOD (experimental)'
    filename_ext = '.mod'
    filter_glob: StringProperty(default='*.mod', options={'HIDDEN'})
    check_existing: BoolProperty(default=False, options={'HIDDEN'})
    output_mode: EnumProperty(name='Output', items=[('AUTO', 'Auto', ''), ('STANDARD', 'Standard Model Only', ''), ('BREAK', 'Break Model Only', '')], default='AUTO')
    smoothing_mode: EnumProperty(name='Smoothing', items=[('KEEP', 'Keep Current Export', 'Keep existing export behavior'),
                                                         ('DIRECT', 'Direct Corner Normals', 'Export Blender corner normals without splitting vertices'),
                                                         ('SPLIT', 'Split Smoothing Boundaries', 'Split vertices at Blender shading boundaries')], default='KEEP')
    distances: FloatVectorProperty(name='LOD distances', size=5, default=(0., 100., 200., 300., 400.))
    lod_count: IntProperty(default=1, options={'HIDDEN'})

    def invoke(self, context, event):
        try:
            self.lod_count, self.distances = initial_lod_settings(context, context.active_object)
        except Exception:
            # Keep the file browser available; execute reports any export error.
            pass
        return super().invoke(context, event)

    def draw(self, context):
        self.layout.label(text='Choose what to export:')
        self.layout.prop(self, 'output_mode')
        self.layout.label(text='- Auto: both, if available')
        self.layout.label(text='- Standard: ship and LODs')
        self.layout.label(text='- Break: debris pieces')
        self.layout.prop(self, 'smoothing_mode')
        self.layout.label(text='- Current: keep existing export')
        self.layout.label(text='- Direct: use Blender normals')
        self.layout.label(text='- Split: detach shading edges')
        if self.output_mode != 'BREAK':
            if self.lod_count > 1:
                self.layout.label(text='LOD switching distances:')
                for index in range(1, min(self.lod_count, 5)):
                    self.layout.prop(self, 'distances', index=index, text=f'LOD {index + 1} distance')

    def execute(self, context):
        try:
            active = context.active_object
            choices = find_export_models(context, active)
            if self.output_mode != 'STANDARD' and 'break' not in choices and choices.get('_skipped_break') and (self.output_mode == 'BREAK' or 'standard' not in choices):
                report_export_warnings(self, [f'Skipped empty break piece: {name}' for name in choices['_skipped_break']])
                return {'CANCELLED'}
            paths = output_paths(self.filepath, self.output_mode, 'standard' in choices, 'break' in choices)
            snapshots = {str(path): destination_snapshot(path) for path in paths.values()}
            if any(snapshot is not None for snapshot in snapshots.values()):
                if bpy.app.background:
                    raise ValueError('Overwrite confirmation requires an interactive Blender session')
                payload = json.dumps({'active': active.name, 'paths': {k: str(v) for k, v in paths.items()}, 'snapshots': snapshots, 'include_empty_break_warnings': self.output_mode != 'STANDARD', 'smoothing_mode': self.smoothing_mode, 'has_distances': self.properties.is_property_set('distances'), 'distances': list(self.distances)})
                result = bpy.ops.export_scene.sfc_mod_confirm('INVOKE_DEFAULT', payload=payload)
                return {'CANCELLED'} if 'CANCELLED' in result else {'FINISHED'}
            outputs, warnings = prepare_selected_outputs(context, active, paths, self.output_mode != 'STANDARD',
                                                        split_angle='BLENDER' if self.smoothing_mode == 'SPLIT' else None,
                                                        direct_normals=self.smoothing_mode == 'DIRECT')
            if self.properties.is_property_set('distances') and 'standard' in paths:
                path = paths['standard']
                outputs[path] = update_lod_distances(outputs[path], distances=self.distances)
            write_export_outputs(outputs, snapshots)
            report_export_warnings(self, warnings)
            return {'FINISHED'}
        except Exception as exc:
            message = (f'Cannot write to {Path(self.filepath).parent}; choose a folder where you can save files'
                       if isinstance(exc, PermissionError) else str(exc))
            self.report({'ERROR'}, f'MOD export failed: {message}')
            return {'CANCELLED'}


def menu_import(self, context):
    self.layout.operator(IMPORT_OT_sfc_mod.bl_idname, text='Starfleet Command 1/2/OP/3 (.mod)')


def menu_export(self, context):
    self.layout.operator(EXPORT_OT_sfc_mod.bl_idname, text='Starfleet Command 1/2/OP/3 (.mod)')


def register():
    bpy.utils.register_class(IMPORT_OT_sfc_mod)
    bpy.utils.register_class(EXPORT_OT_sfc_mod_confirm)
    bpy.utils.register_class(EXPORT_OT_sfc_mod)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.utils.unregister_class(EXPORT_OT_sfc_mod)
    bpy.utils.unregister_class(EXPORT_OT_sfc_mod_confirm)
    bpy.utils.unregister_class(IMPORT_OT_sfc_mod)
