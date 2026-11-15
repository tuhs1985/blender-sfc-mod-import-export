bl_info = {
    'name': 'Starfleet Command 1/2/OP/3 MOD Import/Export',
    'author': 'SFC MOD project',
    'version': (0, 3, 0),
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
import tempfile
import zlib
from pathlib import Path
import bpy
from mathutils import Vector
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .mod_format import parse_model, group_break_polygons, rewrite_records, texture_stem_collisions


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


def import_model(context, filepath):
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
            obj = bpy.data.objects.new(mesh.name, mesh)
            collection.objects.link(obj)
            obj.rotation_euler.x = math.pi / 2
            obj.location = (origin.x, -origin.z, origin.y)
            if is_break:
                obj['mod_piece_id'] = number - 1
                obj['mod_vertex_indices'] = used
                if pivot:
                    obj['mod_pivot_name'] = pivot['name']
                    obj['mod_pivot_position'] = pivot['position']
            else:
                obj['mod_lod_index'] = number - 1
                obj.hide_set(number != 1)
        for point_index, point in enumerate(model['points']):
            obj = bpy.data.objects.new(point['name'], None)
            collection.objects.link(obj)
            x, y, z = point['position']
            obj.location = (x, -z, y)
            obj.empty_display_type = 'SPHERE'
            obj.empty_display_size = 0.15
            obj['mod_name'] = point['name']
            obj['mod_point_index'] = point_index
            obj['mod_initial_blender_name'] = obj.name
            obj['mod_position'] = point['position']
            obj['mod_string_offset'] = point['name_offset']
    except Exception:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)
        raise
    return warnings


def prepare_standard_export(collection, destination):
    """Prepare a conservative export from one newly imported collection."""
    encoded = collection.get('mod_source_zlib_base64')
    if not encoded:
        raise ValueError('Source metadata missing; re-import the original model')
    source = zlib.decompress(base64.b64decode(encoded, validate=True))
    model = parse_model(source)
    if str(collection.get('mod_source_filename', '')).casefold().endswith('_brk.mod'):
        raise ValueError('Break-model export is not supported yet')
    if collection.children:
        raise ValueError('Nested model collections are not supported yet')
    objects = list(collection.objects)
    meshes = [obj for obj in objects if obj.type == 'MESH' and 'mod_lod_index' in obj]
    points = [obj for obj in objects if obj.type == 'EMPTY' and 'mod_point_index' in obj]
    if len(meshes) + len(points) != len(objects) or len(meshes) != len(model['meshes']) or len(points) != len(model['points']):
        raise ValueError('Added, removed, or unrecognized model objects are not supported yet')
    mesh_map = {int(obj['mod_lod_index']): obj for obj in meshes}
    point_map = {int(obj['mod_point_index']): obj for obj in points}
    if sorted(mesh_map) != list(range(len(meshes))) or sorted(point_map) != list(range(len(points))):
        raise ValueError('Missing or duplicate LOD or point identifiers')
    if len(meshes) > 1:
        prefixes = set()
        for i, obj in mesh_map.items():
            match = re.fullmatch(r'(.+)_(\d+)', obj.name)
            if not match or int(match.group(2)) != i + 1:
                raise ValueError(f'LOD name and stored ID conflict: {obj.name}')
            prefixes.add(match.group(1).casefold())
        if len(prefixes) != 1:
            raise ValueError('LOD names must share a prefix')
    bpy.context.view_layer.update()
    warnings = []
    image_paths = []
    base_materials = list(mesh_map[0].data.materials)
    if len(base_materials) != len(model['materials']):
        raise ValueError('Adding or removing material slots is not supported yet')

    def image_reference(image, previous):
        if not image or not image.filepath:
            raise ValueError('Assigned image has no file path')
        absolute = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
        image_paths.append(str(absolute))
        if os.path.normcase(str(absolute.parent)) != os.path.normcase(str(Path(destination).resolve().parent)):
            warnings.append(f'Texture is outside save directory: {absolute}')
        return previous if absolute.stem.casefold() == previous.casefold() else absolute.name

    for i, (mat, saved) in enumerate(zip(base_materials, model['materials'])):
        if mat is not None and 'mod_shader_defaults' not in mat:
            raise ValueError('Material source metadata missing; re-import with the current add-on')
        if mat is None or mat.get('mod_flags') != saved['flags'] or mat.get('mod_record_hex') != saved['raw'].hex() or not mat.use_nodes:
            raise ValueError(f'Material slot {i} was replaced or altered in an unsupported way')
        shader = mat.node_tree.nodes.get('Principled BSDF')
        if shader is None:
            raise ValueError(f'Material slot {i} has no supported shader')
        output = mat.node_tree.nodes.get('Material Output')
        if mat.get('mod_shader_defaults') != shader_defaults(shader) or not output or not output.inputs['Surface'].is_linked or output.inputs['Surface'].links[0].from_node != shader:
            raise ValueError(f'Unsupported shader edits in material slot {i}')
        base_links = shader.inputs['Base Color'].links
        diffuse_node = base_links[0].from_node if base_links else None
        if diffuse_node and diffuse_node.type != 'TEX_IMAGE':
            raise ValueError(f'Material slot {i} uses an unsupported diffuse node')
        if diffuse_node and diffuse_node.inputs['Vector'].is_linked:
            raise ValueError(f'Unsupported texture coordinates in material slot {i}')
        if saved['diffuse'] is None and diffuse_node:
            raise ValueError('Adding a diffuse map is not supported yet')
        if saved['diffuse'] is not None:
            if diffuse_node:
                saved['diffuse'] = image_reference(diffuse_node.image, saved['diffuse'])
            elif mat.get('mod_diffuse_loaded', False):
                raise ValueError(f'Diffuse map was disconnected in material slot {i}')
            else:
                warnings.append(f'Texture reference unresolved: {saved["diffuse"]}')
        illum_nodes = [node for node in mat.node_tree.nodes if node.type == 'TEX_IMAGE' and node.label == 'OP illumination map']
        if len(illum_nodes) > 1 or (illum_nodes and saved['illumination'] is None):
            raise ValueError(f'Unsupported illumination nodes in material slot {i}')
        if not illum_nodes and shader.inputs['Emission Color'].is_linked:
            raise ValueError(f'Unsupported illumination connections in material slot {i}')
        if saved['illumination'] is not None:
            if illum_nodes:
                if illum_nodes[0].inputs['Vector'].is_linked:
                    raise ValueError(f'Unsupported illumination coordinates in material slot {i}')
                if diffuse_node:
                    emission = shader.inputs['Emission Color'].links
                    mix = emission[0].from_node if emission else None
                    if not mix or mix.type != 'MIX_RGB' or mix.blend_type != 'MULTIPLY' or not mix.inputs[1].is_linked or not mix.inputs[2].is_linked or mix.inputs[1].links[0].from_node != diffuse_node or mix.inputs[2].links[0].from_node != illum_nodes[0]:
                        raise ValueError(f'Unsupported illumination connections in material slot {i}')
                saved['illumination'] = image_reference(illum_nodes[0].image, saved['illumination'])
            elif mat.get('mod_illumination_loaded', False):
                raise ValueError(f'Illumination map was removed in material slot {i}')
            else:
                warnings.append(f'Texture reference unresolved: {saved["illumination"]}')
    collisions = texture_stem_collisions(image_paths)
    if collisions:
        raise ValueError('Different images share a MOD texture stem: ' + ', '.join(sorted(collisions)))
    for i, original in enumerate(model['meshes']):
        obj = mesh_map[i]
        mesh = obj.data
        records = json.dumps([(p['raw_header'] + b''.join(c['raw'] for c in p['corners'])).hex() for p in original['polygons']])
        if mesh.get('mod_polygon_records') != records:
            raise ValueError(f'Polygon source metadata changed or missing in {obj.name}')
        if obj.parent or obj.constraints or obj.modifiers or mesh.shape_keys or len(mesh.vertices) != len(original['vertices']) or len(mesh.polygons) != len(original['polygons']):
            raise ValueError(f'Unsupported topology or parenting in {obj.name}')
        if list(mesh.materials) != base_materials or not mesh.uv_layers.active or mesh.has_custom_normals or any(edge.use_edge_sharp for edge in mesh.edges):
            raise ValueError(f'Unsupported materials, UVs or custom normals in {obj.name}')
        expected_rotation = (Vector((math.pi / 2, 0, 0)).x, 0.0, 0.0)
        if (obj.rotation_mode != 'XYZ' or tuple(obj.location) != (0.0, 0.0, 0.0) or
                tuple(obj.rotation_euler) != expected_rotation or tuple(obj.scale) != (1.0, 1.0, 1.0) or
                tuple(obj.delta_location) != (0.0, 0.0, 0.0) or tuple(obj.delta_rotation_euler) != (0.0, 0.0, 0.0) or
                tuple(obj.delta_scale) != (1.0, 1.0, 1.0)):
            raise ValueError(f'Vertex or object transforms changed in {obj.name}; normal export is not ready')
        for vertex, xyz in zip(mesh.vertices, original['vertices']):
            if tuple(vertex.co) != tuple(xyz):
                raise ValueError(f'Vertex or object transforms changed in {obj.name}; normal export is not ready')
        for face, polygon in zip(mesh.polygons, original['polygons']):
            if face.use_smooth or tuple(face.vertices) != tuple(polygon['corners'][k]['index'] for k in (1, 0, 2)):
                raise ValueError(f'Unsupported topology or smoothing change in {obj.name}')
            polygon['material'] = face.material_index
            for loop, corner_index in zip(face.loop_indices, (1, 0, 2)):
                polygon['corners'][corner_index]['uv'] = tuple(mesh.uv_layers.active.data[loop].uv)
    for i, point in enumerate(model['points']):
        obj = point_map[i]
        if obj.parent or obj.constraints:
            raise ValueError(f'Parented or constrained point is unsupported: {obj.name}')
        if (obj.rotation_mode != 'XYZ' or tuple(obj.rotation_euler) != (0.0, 0.0, 0.0) or
                tuple(obj.scale) != (1.0, 1.0, 1.0) or tuple(obj.delta_location) != (0.0, 0.0, 0.0) or
                tuple(obj.delta_rotation_euler) != (0.0, 0.0, 0.0) or tuple(obj.delta_scale) != (1.0, 1.0, 1.0)):
            raise ValueError(f'Point rotation or scale is not supported: {obj.name}')
        initial_name = obj.get('mod_initial_blender_name')
        if initial_name is None:
            raise ValueError('Point source metadata missing; re-import the original model')
        point['name'] = point['name'] if obj.name == initial_name else obj.name
        world = obj.matrix_world.translation
        point['position'] = (world.x, world.z, -world.y)
    return rewrite_records(source, model['points'], model['materials'], model['meshes']), list(dict.fromkeys(warnings))


class IMPORT_OT_sfc_mod(bpy.types.Operator, ImportHelper):
    bl_idname = 'import_scene.sfc_mod'
    bl_label = 'Import SFC 1/2/OP/3 MOD'
    filename_ext = '.mod'
    filter_glob: StringProperty(default='*.mod;*.MOD', options={'HIDDEN'})

    def execute(self, context):
        try:
            warnings = import_model(context, self.filepath)
        except Exception as exc:
            self.report({'ERROR'}, f'MOD import failed: {exc}')
            return {'CANCELLED'}
        if warnings:
            self.report({'WARNING'}, f'{len(warnings)} import warning(s): {warnings[0]}')
        return {'FINISHED'}


class EXPORT_OT_sfc_mod(bpy.types.Operator, ExportHelper):
    bl_idname = 'export_scene.sfc_mod'
    bl_label = 'Export SFC 1/2/OP/3 MOD (experimental)'
    filename_ext = '.mod'
    filter_glob: StringProperty(default='*.mod', options={'HIDDEN'})

    def execute(self, context):
        active = context.active_object
        collections = [c for c in active.users_collection if 'mod_source_zlib_base64' in c] if active else []
        if len(collections) != 1:
            self.report({'ERROR'}, 'Select an object in exactly one imported model collection')
            return {'CANCELLED'}
        temp_path = None
        try:
            data, warnings = prepare_standard_export(collections[0], self.filepath)
            destination = Path(self.filepath)
            with tempfile.NamedTemporaryFile(mode='wb', dir=destination.parent, prefix='.sfc-mod-', delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, destination)
            temp_path = None
        except Exception as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            self.report({'ERROR'}, f'MOD export failed: {exc}')
            return {'CANCELLED'}
        if warnings:
            detail = bpy.data.texts.new('SFC MOD Export Warnings')
            detail.write('\n'.join(warnings))
            self.report({'WARNING'}, f'{len(warnings)} texture warning(s). See Text Editor: {detail.name}')
        return {'FINISHED'}


def menu_import(self, context):
    self.layout.operator(IMPORT_OT_sfc_mod.bl_idname, text='Starfleet Command 1/2/OP/3 (.mod)')


def menu_export(self, context):
    self.layout.operator(EXPORT_OT_sfc_mod.bl_idname, text='Starfleet Command 1/2/OP/3 (.mod)')


def register():
    bpy.utils.register_class(IMPORT_OT_sfc_mod)
    bpy.utils.register_class(EXPORT_OT_sfc_mod)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.utils.unregister_class(EXPORT_OT_sfc_mod)
    bpy.utils.unregister_class(IMPORT_OT_sfc_mod)
