bl_info = {
    'name': 'Starfleet Command 1/2/OP/3 MOD Import',
    'author': 'SFC MOD project',
    'version': (0, 2, 5),
    'blender': (4, 3, 0),
    'location': 'File > Import',
    'description': 'Import Starfleet Command MOD models (experimental)',
    'category': 'Import-Export',
}

import math
import json
import re
from pathlib import Path
import bpy
from mathutils import Vector
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
from .mod_format import parse_model, group_break_polygons


def import_model(context, filepath):
    path = Path(filepath)
    is_break = path.stem.casefold().endswith('_brk')
    model = parse_model(path.read_bytes())
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
                if image:
                    diffuse = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    diffuse.image = image
                    mat.node_tree.links.new(diffuse.outputs['Color'], shader.inputs['Base Color'])
            if source['illumination']:
                mat['mod_illumination_stem'] = source['illumination']
                image = texture(source['illumination'])
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
        if is_break:
            source = model['meshes'][0]
            parts = [(group + 1, {'vertices': source['vertices'], 'polygons': polys}, pivots.get(group))
                     for group, polys in sorted(groups.items())]
        else:
            parts = [(number, source, None) for number, source in enumerate(model['meshes'], 1)]
        for number, source, pivot in parts:
            name = f'{path.stem}_{number}' if is_break else f'{path.stem} LOD {number}'
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
        for point in model['points']:
            obj = bpy.data.objects.new(point['name'], None)
            collection.objects.link(obj)
            x, y, z = point['position']
            obj.location = (x, -z, y)
            obj.empty_display_type = 'SPHERE'
            obj.empty_display_size = 0.15
            obj['mod_name'] = point['name']
            obj['mod_position'] = point['position']
            obj['mod_string_offset'] = point['name_offset']
    except Exception:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)
        raise
    return warnings


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


def menu_import(self, context):
    self.layout.operator(IMPORT_OT_sfc_mod.bl_idname, text='Starfleet Command 1/2/OP/3 (.mod)')


def register():
    bpy.utils.register_class(IMPORT_OT_sfc_mod)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.utils.unregister_class(IMPORT_OT_sfc_mod)
