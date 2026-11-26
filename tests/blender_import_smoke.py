"""Run with Blender's --background --factory-startup --python option."""
import struct
import base64
import zlib
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path
import bpy
import bmesh

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / 'addon'))
import io_scene_sfc_mod as addon
assert addon.bl_info['name'] == 'Starfleet Command 1/2/OP/3 MOD Import/Export'
addon.register()
large_mesh = bpy.data.meshes.new('index_boundary_mesh')
large_mesh.from_pydata([(float(i), 0., 0.) for i in range(65536)], [], [(0, 1, 65535)])
large_object = bpy.data.objects.new('index_boundary', large_mesh)
bpy.context.scene.collection.objects.link(large_object)
assert len(addon.authored_geometry(bpy.context, large_object, lambda mat: 0)['vertices']) == 65536
bpy.data.objects.remove(large_object, do_unlink=True)
over_mesh = bpy.data.meshes.new('over_index_boundary_mesh')
over_mesh.from_pydata([(float(i), 0., 0.) for i in range(65537)], [], [(0, 1, 65535)])
over_object = bpy.data.objects.new('over_index_boundary', over_mesh)
bpy.context.scene.collection.objects.link(over_object)
try:
    addon.authored_geometry(bpy.context, over_object, lambda mat: 0)
    raise AssertionError('Mesh exceeding the 16-bit vertex limit was accepted')
except ValueError as exc:
    assert 'vertex index limit' in str(exc)
bpy.data.objects.remove(over_object, do_unlink=True)
mode_props = bpy.ops.export_scene.sfc_mod.get_rna_type().properties['output_mode']
assert mode_props.default == 'AUTO'
assert [item.identifier for item in mode_props.enum_items] == ['AUTO', 'STANDARD', 'BREAK']
class ExportLayoutRecorder:
    def __init__(self):
        self.labels = []
        self.properties = []
    def label(self, *, text):
        self.labels.append(text)
    def prop(self, owner, name):
        self.properties.append(name)
layout = ExportLayoutRecorder()
addon.EXPORT_OT_sfc_mod.draw(type('FakeExport', (), {'layout': layout})(), None)
assert layout.properties == ['output_mode']
assert any('Auto' in text for text in layout.labels)
assert any('Standard' in text for text in layout.labels)
assert any('Break' in text for text in layout.labels)
confirm_properties = bpy.ops.export_scene.sfc_mod_confirm.get_rna_type().properties
assert confirm_properties['overwrite_standard'].default is True
assert confirm_properties['overwrite_break'].default is True
with patch('builtins.open', side_effect=PermissionError('Access denied')) as denied_open:
    try:
        addon.open_export_temp(Path(tempfile.gettempdir()))
        raise AssertionError('Permission error was ignored')
    except PermissionError:
        assert denied_open.call_count == 1

def chunk(tag, data):
    return tag + struct.pack('<I', len(data)) + data + b'\0' * (-len(data) % 4)

strings = b'hardpoint1\0hull\0hulli\0'
material = struct.pack('<9I', 0x21, 0, 0, 0, 0, 0, 11, 0, 16)
points = struct.pack('<3fI', 1, 2, 3, 0)
vertices = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
corners = b''.join(struct.pack('<I3f2fI', i, 0, 0, 1, 0, 0, 0) for i in range(3))
geometry = struct.pack('<II', 3, 1) + chunk(b'VTXS', vertices) + chunk(b'POLY', struct.pack('<II3f', 3, 0, 0, 0, 1) + corners)
body = bytes(36) + chunk(b'STRS', strings) + chunk(b'PNTS', points) + chunk(b'MATS', material) + chunk(b'MOD0', geometry)
with tempfile.TemporaryDirectory() as folder:
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4)
    sphere = bpy.context.active_object
    sphere_file = Path(folder) / 'new_sphere.mod'
    assert bpy.ops.export_scene.sfc_mod(filepath=str(sphere_file)) == {'FINISHED'}
    sphere_model = addon.parse_model(sphere_file.read_bytes())
    assert len(sphere_model['meshes']) == 1
    assert len(sphere_model['meshes'][0]['polygons']) > 0
    assert len(sphere_model['materials']) >= 1
    authored = bpy.data.collections.new('Authored test ship')
    bpy.context.scene.collection.children.link(authored)
    authored.objects.link(sphere)
    for collection in list(sphere.users_collection):
        if collection != authored:
            collection.objects.unlink(sphere)
    sphere.name = 'testship_1'
    lod2 = sphere.copy()
    lod2.data = sphere.data.copy()
    lod2.name = 'testship_2'
    authored.objects.link(lod2)
    point = bpy.data.objects.new('hardpoint1', None)
    point.location = (1., 2., 3.)
    authored.objects.link(point)
    break_piece = sphere.copy()
    break_piece.data = sphere.data.copy()
    break_piece.name = 'testship_brk_1'
    authored.objects.link(break_piece)
    empty_break_mesh = bpy.data.meshes.new('empty authored break mesh')
    empty_break = bpy.data.objects.new('testship_brk_3', empty_break_mesh)
    authored.objects.link(empty_break)
    unrelated_piece = sphere.copy()
    unrelated_piece.data = sphere.data.copy()
    unrelated_piece.name = 'other_brk_1'
    authored.objects.link(unrelated_piece)
    choices = addon.find_export_models(bpy.context, sphere)
    assert choices['standard'][1] == sphere
    assert choices['break'][1] == break_piece
    mat = bpy.data.materials.new('test hull')
    mat.use_nodes = True
    diffuse = bpy.data.images.new('diffuse', width=1, height=1)
    diffuse.filepath = str(Path(folder) / 'hull.bmp')
    illum = bpy.data.images.new('illum', width=1, height=1)
    illum.filepath = str(Path(folder) / 'hulli.bmp')
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.name = 'Artist renamed shader'
    diffuse_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    diffuse_node.image = diffuse
    mat.node_tree.links.new(diffuse_node.outputs['Color'], shader.inputs['Base Color'])
    illum_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    illum_node.image = illum
    mix = mat.node_tree.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mat.node_tree.links.new(diffuse_node.outputs['Color'], mix.inputs[1])
    mat.node_tree.links.new(illum_node.outputs['Color'], mix.inputs[2])
    mat.node_tree.links.new(mix.outputs['Color'], shader.inputs['Emission Color'])
    sphere.data.materials.append(mat)
    lod2.data.materials.append(mat)
    authored_file = Path(folder) / 'authored.mod'
    assert bpy.ops.export_scene.sfc_mod(filepath=str(authored_file)) == {'FINISHED'}
    authored_model = addon.parse_model(authored_file.read_bytes())
    assert len(authored_model['meshes']) == 2
    authored_break_model = addon.parse_model((Path(folder) / 'authored_brk.mod').read_bytes())
    assert sorted(addon.group_break_polygons(authored_break_model['meshes'][0])) == [0]
    _, authored_empty_warnings = addon.prepare_new_mesh_export(bpy.context, break_piece, Path(folder) / 'authored_brk.mod', break_mode=True)
    assert any('testship_brk_3' in warning and 'skip' in warning.lower() for warning in authored_empty_warnings)
    assert authored_model['points'][0]['name'] == 'hardpoint1'
    assert authored_model['points'][0]['position'] == (1., 3., -2.)
    assert authored_model['materials'][0]['diffuse'] == 'hull'
    assert authored_model['materials'][0]['illumination'] == 'hulli'
    auto_standard = Path(folder) / 'auto_ship.mod'
    auto_break = Path(folder) / 'auto_ship_brk.mod'
    auto_standard.write_bytes(b'original standard')
    auto_break.write_bytes(b'original break')
    state = {'active': sphere.name, 'paths': {'standard': str(auto_standard), 'break': str(auto_break)},
             'snapshots': {str(p): addon.destination_snapshot(p) for p in (auto_standard, auto_break)}}
    import json
    assert bpy.ops.export_scene.sfc_mod_confirm(payload=json.dumps(state), overwrite_standard=True, overwrite_break=False) == {'FINISHED'}
    assert addon.parse_model(auto_standard.read_bytes())['meshes']
    assert auto_break.read_bytes() == b'original break'
    before_authored_import = set(bpy.data.objects)
    addon.import_model(bpy.context, str(authored_file))
    authored_import = set(bpy.data.objects) - before_authored_import
    assert len([item for item in authored_import if item.type == 'MESH']) == 2
    assert any(item.type == 'EMPTY' and item.name.startswith('hardpoint1') for item in authored_import)
    for item in authored_import:
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.objects.remove(lod2, do_unlink=True)
    bpy.data.objects.remove(break_piece, do_unlink=True)
    bpy.data.objects.remove(empty_break, do_unlink=True)
    bpy.data.objects.remove(unrelated_piece, do_unlink=True)
    bpy.data.objects.remove(point, do_unlink=True)
    before_sphere_import = set(bpy.data.objects)
    addon.import_model(bpy.context, str(sphere_file))
    imported_sphere = next(o for o in set(bpy.data.objects) - before_sphere_import if o.type == 'MESH')
    assert len(imported_sphere.data.polygons) == len(sphere_model['meshes'][0]['polygons'])
    bm = bmesh.new()
    bm.from_mesh(imported_sphere.data)
    bm.faces.ensure_lookup_table()
    bm.faces.remove(bm.faces[0])
    bm.to_mesh(imported_sphere.data)
    bm.free()
    edited, edit_warnings = addon.prepare_standard_export(imported_sphere.users_collection[0], sphere_file)
    assert not any('Edited topology' in warning or 'vertex edit' in warning for warning in edit_warnings)
    edited_model = addon.parse_model(edited)
    assert len(edited_model['meshes'][0]['polygons']) == len(sphere_model['meshes'][0]['polygons']) - 1
    edited_path = Path(folder) / 'open_sphere.mod'
    edited_path.write_bytes(edited)
    before_open_import = set(bpy.data.objects)
    addon.import_model(bpy.context, str(edited_path))
    open_sphere = next(o for o in set(bpy.data.objects) - before_open_import if o.type == 'MESH')
    assert len(open_sphere.data.polygons) == len(edited_model['meshes'][0]['polygons'])
    bpy.data.objects.remove(open_sphere, do_unlink=True)
    bpy.data.objects.remove(imported_sphere, do_unlink=True)
    bpy.data.objects.remove(sphere, do_unlink=True)
    path = Path(folder) / 'ship.mod'
    original = b'MDLS' + struct.pack('<I', len(body)) + body
    path.write_bytes(original)
    before = set(bpy.data.objects)
    warnings = addon.import_model(bpy.context, str(path))
    created = set(bpy.data.objects) - before
    imported_collection = next(c for c in bpy.data.collections if c.name == 'SFC MOD: ship')
    assert zlib.decompress(base64.b64decode(imported_collection['mod_source_zlib_base64'])) == original
    assert len(warnings) == 2
    assert sorted(o.type for o in created) == ['EMPTY', 'MESH']
    assert next(o for o in created if o.type == 'EMPTY')['mod_name'] == 'hardpoint1'
    assert len(next(o for o in created if o.type == 'MESH').data.materials) == 1
    exported, export_warnings = addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
    assert exported == original
    exported_mesh = next(o for o in created if o.type == 'MESH')
    new_lod = exported_mesh.copy()
    new_lod.data = exported_mesh.data.copy()
    del new_lod['mod_lod_index']
    new_lod.name = 'ship_2'
    imported_collection.objects.link(new_lod)
    lod_data, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'new_lod.mod')
    assert len(addon.parse_model(lod_data)['meshes']) == 2
    new_lod['mod_lod_index'] = 0
    original_mesh_name = exported_mesh.name
    exported_mesh.name = 'zzz_renamed_original'
    copied_lod, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'copied_lod.mod')
    assert len(addon.parse_model(copied_lod)['meshes']) == 2
    exported_mesh.name = original_mesh_name
    del new_lod['mod_lod_index']
    imported_collection.objects.unlink(exported_mesh)
    removed_lod_data, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'removed_lod.mod')
    assert len(addon.parse_model(removed_lod_data)['meshes']) == 1
    imported_collection.objects.link(exported_mesh)
    bpy.data.objects.remove(new_lod, do_unlink=True)
    exported_mesh.location.x = 2.
    bpy.context.view_layer.update()
    transformed, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'transformed.mod')
    assert addon.parse_model(transformed)['meshes'][0]['vertices'][0][0] == 2.
    assert abs(struct.unpack_from('<f', transformed, 12)[0] - 3.) < 1e-5
    exported_mesh.location.x = 0.
    parent = bpy.data.objects.new('test parent', None)
    bpy.context.scene.collection.objects.link(parent)
    parent.location.x = 3.
    exported_mesh.parent = parent
    bpy.context.view_layer.update()
    parented, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'parented.mod')
    assert abs(addon.parse_model(parented)['meshes'][0]['vertices'][0][0] - 3.) < 1e-5
    exported_mesh.parent = None
    bpy.data.objects.remove(parent, do_unlink=True)
    exported_mesh.shape_key_add(name='Basis')
    key = exported_mesh.shape_key_add(name='move')
    key.data[0].co.x += 1.
    key.value = 0.5
    bpy.context.view_layer.update()
    shaped, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'shaped.mod')
    assert abs(addon.parse_model(shaped)['meshes'][0]['vertices'][0][0] - 0.5) < 1e-5
    exported_mesh.shape_key_clear()
    modifier = exported_mesh.modifiers.new('test solidify', 'SOLIDIFY')
    bpy.context.view_layer.update()
    modified, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'modified.mod')
    assert len(addon.parse_model(modified)['meshes'][0]['polygons']) > 1
    exported_mesh.modifiers.remove(modifier)
    original_uv = exported_mesh.data.uv_layers.active
    original_uv_values = [tuple(item.uv) for item in original_uv.data]
    exported_mesh.data.uv_layers.remove(original_uv)
    no_uv, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'no_uv.mod')
    assert addon.parse_model(no_uv)['meshes'][0]['polygons'][0]['corners'][0]['uv'] == (0., 0.)
    restored_uv = exported_mesh.data.uv_layers.new(name='MOD UV')
    for item, value in zip(restored_uv.data, original_uv_values):
        item.uv = value
    added_standard_point = bpy.data.objects.new('damagepoint_new_standard', None)
    added_standard_point.location = (2., 3., 4.)
    imported_collection.objects.link(added_standard_point)
    added_standard_mat = bpy.data.materials.new('standard extra material')
    added_standard_mat.use_nodes = True
    added_shader = added_standard_mat.node_tree.nodes.get('Principled BSDF')
    standard_diffuse = bpy.data.images.new('standard_new_diffuse', width=1, height=1)
    standard_diffuse.filepath = str(Path(folder) / 'new_standard.bmp')
    standard_diffuse_node = added_standard_mat.node_tree.nodes.new('ShaderNodeTexImage')
    standard_diffuse_node.image = standard_diffuse
    added_standard_mat.node_tree.links.new(standard_diffuse_node.outputs['Color'], added_shader.inputs['Base Color'])
    standard_illum = bpy.data.images.new('standard_new_illum', width=1, height=1)
    standard_illum.filepath = str(Path(folder) / 'new_standard_i.bmp')
    standard_illum_node = added_standard_mat.node_tree.nodes.new('ShaderNodeTexImage')
    standard_illum_node.image = standard_illum
    added_standard_mat.node_tree.links.new(standard_illum_node.outputs['Color'], added_shader.inputs['Emission Color'])
    foreign_mat = bpy.data.materials.new('material from another model')
    foreign_mat['mod_record_hex'] = struct.pack('<7I', 1, 0, 0, 0, 0, 0, 0).hex()
    foreign_mat['mod_diffuse_stem'] = 'foreign_texture'
    foreign_mat['mod_diffuse_loaded'] = False
    exported_mesh.data.materials.append(added_standard_mat)
    exported_mesh.data.materials.append(foreign_mat)
    exported_mesh.data.polygons[0].material_index = 1
    bpy.context.view_layer.update()
    edited_standard, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'changed.mod')
    edited_standard_model = addon.parse_model(edited_standard)
    assert len(edited_standard_model['points']) == 2
    assert any(p['name'] == 'damagepoint_new_standard' and p['position'] == (2., 4., -3.) for p in edited_standard_model['points'])
    assert len(edited_standard_model['materials']) == 3
    assert edited_standard_model['meshes'][0]['polygons'][0]['material'] == 1
    assert edited_standard_model['materials'][1]['diffuse'] == 'new_standard'
    assert edited_standard_model['materials'][1]['illumination'] == 'new_standard_i'
    assert edited_standard_model['materials'][2]['diffuse'] == 'foreign_texture'
    old_standard_point = next(obj for obj in created if obj.type == 'EMPTY')
    imported_collection.objects.unlink(old_standard_point)
    removed_standard, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'changed.mod')
    removed_standard_model = addon.parse_model(removed_standard)
    assert len(removed_standard_model['points']) == 1
    assert removed_standard_model['points'][0]['name'] == 'damagepoint_new_standard'
    imported_collection.objects.link(old_standard_point)
    bpy.data.objects.remove(added_standard_point, do_unlink=True)
    exported_mesh.data.materials.pop(index=2)
    exported_mesh.data.materials.pop(index=1)
    exported_mesh.name = 'any_single_mesh_name'
    assert addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')[0] == original
    bpy.context.view_layer.objects.active = exported_mesh
    exported_mesh.select_set(True)
    target = Path(folder) / 'export.mod'
    assert bpy.ops.export_scene.sfc_mod(filepath=str(target)) == {'FINISHED'}
    assert target.read_bytes() == original
    shader = exported_mesh.data.materials[0].node_tree.nodes.get('Principled BSDF')
    old_roughness = shader.inputs['Roughness'].default_value
    shader.inputs['Roughness'].default_value = 0.123
    _, shader_warnings = addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
    assert any('shader settings' in warning for warning in shader_warnings)
    destination = Path(folder) / 'protected.mod'
    destination.write_bytes(b'unchanged')
    bpy.context.view_layer.objects.active = exported_mesh
    exported_mesh.select_set(True)
    try:
        result = bpy.ops.export_scene.sfc_mod(filepath=str(destination))
        assert result == {'CANCELLED'}
    except RuntimeError:
        pass
    assert destination.read_bytes() == b'unchanged'
    shader.inputs['Roughness'].default_value = old_roughness
    exported_mesh.data.uv_layers.active.data[0].uv = (0.5, 0.25)
    point = next(o for o in created if o.type == 'EMPTY')
    point.location = (4., -6., 5.)
    point.rotation_euler.x = 0.25
    rotated_point_export, _ = addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
    assert addon.parse_model(rotated_point_export)['points'][0]['position'] == (4., 5., 6.)
    point.rotation_euler.x = 0.0
    exported, export_warnings = addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
    model = addon.parse_model(exported)
    assert model['points'][0]['position'] == (4., 5., 6.)
    assert model['meshes'][0]['polygons'][0]['corners'][1]['uv'] == (0.5, 0.25)
    exported_mesh.data.vertices[0].co.x += 0.000001
    vertex_edited, vertex_warnings = addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
    assert not any('vertex edit' in warning for warning in vertex_warnings)
    assert abs(addon.parse_model(vertex_edited)['meshes'][0]['vertices'][0][0] - 0.000001) < 1e-8
    image = bpy.data.images.new('test_texture', width=1, height=1)
    image.filepath_raw = str(Path(folder) / 'hull.png')
    image.file_format = 'PNG'
    image.save()
    before = set(bpy.data.objects)
    warnings = addon.import_model(bpy.context, str(path))
    imported = next(o for o in set(bpy.data.objects) - before if o.type == 'MESH')
    nodes = imported.data.materials[0].node_tree.nodes
    assert any(n.type == 'TEX_IMAGE' and n.image and n.image.filepath.endswith('hull.png') for n in nodes)
    assert len(warnings) == 1
    other_directory = Path(folder) / 'other'
    other_directory.mkdir()
    exported, location_warnings = addon.prepare_standard_export(imported.users_collection[0], other_directory / 'ship.mod')
    assert any('outside save directory' in warning for warning in location_warnings)
    new_image = bpy.data.images.new('replacement', width=1, height=1)
    new_image.filepath_raw = str(Path(folder) / 'thisdamntexture.png')
    new_image.file_format = 'PNG'
    new_image.save()
    next(n for n in nodes if n.type == 'TEX_IMAGE').image = new_image
    renamed_shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    renamed_shader.name = 'My custom shader name'
    exported, _ = addon.prepare_standard_export(imported.users_collection[0], Path(folder) / 'ship.mod')
    assert addon.parse_model(exported)['materials'][0]['diffuse'] == 'thisdamntexture'
    generated_image = bpy.data.images.new('unsaved_texture', width=1, height=1)
    next(n for n in nodes if n.type == 'TEX_IMAGE').image = generated_image
    exported, generated_warnings = addon.prepare_standard_export(imported.users_collection[0], Path(folder) / 'ship.mod')
    assert addon.parse_model(exported)['materials'][0]['diffuse'] == 'hull'
    assert any('no file' in warning.lower() for warning in generated_warnings)
    image.filepath_raw = str(Path(folder) / 'hull.bmp')
    image.file_format = 'BMP'
    image.save()
    before = set(bpy.data.objects)
    warnings = addon.import_model(bpy.context, str(path))
    imported = next(o for o in set(bpy.data.objects) - before if o.type == 'MESH')
    assert any('Ambiguous texture: hull' in warning for warning in warnings)
    assert not any(n.type == 'TEX_IMAGE' for n in imported.data.materials[0].node_tree.nodes)
    path.write_bytes(b'broken')
    before = set(bpy.data.objects)
    try:
        addon.import_model(bpy.context, str(path))
        raise AssertionError('Malformed model was accepted')
    except ValueError:
        assert set(bpy.data.objects) == before
    print('PASS missing textures and malformed input')
    break_path = Path(folder) / 'ship_brk.mod'
    break_path.write_bytes(b'MDLS' + struct.pack('<I', len(body)) + body)
    before = set(bpy.data.objects)
    warnings = addon.import_model(bpy.context, str(break_path))
    pieces = [o for o in set(bpy.data.objects) - before if o.type == 'MESH']
    assert len(pieces) == 1 and pieces[0]['mod_piece_id'] == 0
    assert pieces[0].name == 'ship_brk_1'
    assert 'mod_pivot_name' not in pieces[0]
    assert not any('pivot' in warning for warning in warnings)
    exported_break, _ = addon.prepare_break_export(bpy.context, pieces[0].users_collection[0], break_path)
    break_model = addon.parse_model(exported_break)
    assert sorted(addon.group_break_polygons(break_model['meshes'][0])) == [0]
    assert len(break_model['points']) == 1
    break_collection = pieces[0].users_collection[0]
    empty_imported_mesh = bpy.data.meshes.new('empty imported break mesh')
    empty_imported = bpy.data.objects.new('ship_brk_2', empty_imported_mesh)
    empty_imported['mod_piece_id'] = 0
    break_collection.objects.link(empty_imported)
    nonempty_export, empty_piece_warnings = addon.prepare_break_export(bpy.context, break_collection, break_path)
    assert sorted(addon.group_break_polygons(addon.parse_model(nonempty_export)['meshes'][0])) == [0]
    assert any('ship_brk_2' in warning and 'skip' in warning.lower() for warning in empty_piece_warnings)
    new_piece = pieces[0].copy()
    new_piece.data = pieces[0].data.copy()
    del new_piece['mod_piece_id']
    new_piece.name = 'ship_brk_99'
    break_collection.objects.link(new_piece)
    expanded_break, _ = addon.prepare_break_export(bpy.context, break_collection, break_path)
    assert sorted(addon.group_break_polygons(addon.parse_model(expanded_break)['meshes'][0])) == [0, 98]
    new_piece['mod_piece_id'] = 0
    copied_piece, _ = addon.prepare_break_export(bpy.context, break_collection, break_path)
    assert sorted(addon.group_break_polygons(addon.parse_model(copied_piece)['meshes'][0])) == [0, 98]
    bpy.data.objects.remove(new_piece, do_unlink=True)
    bpy.data.objects.remove(empty_imported, do_unlink=True)
    added_point = bpy.data.objects.new('damagepoint_new', None)
    added_point.location = (2., 3., 4.)
    break_collection.objects.link(added_point)
    break_mat = pieces[0].data.materials[0]
    break_shader = break_mat.node_tree.nodes.get('Principled BSDF')
    changed_image = bpy.data.images.new('changed_break', width=1, height=1)
    changed_image.filepath = str(Path(folder) / 'changed_break.bmp')
    image_node = break_mat.node_tree.nodes.new('ShaderNodeTexImage')
    image_node.image = changed_image
    break_mat.node_tree.links.new(image_node.outputs['Color'], break_shader.inputs['Base Color'])
    extra_mat = bpy.data.materials.new('new break material')
    pieces[0].data.materials.append(extra_mat)
    pieces[0].data.polygons[0].material_index = 1
    bpy.context.view_layer.update()
    changed_break, _ = addon.prepare_break_export(bpy.context, break_collection, break_path)
    changed_model = addon.parse_model(changed_break)
    assert len(changed_model['points']) == 2
    assert any(p['name'] == 'damagepoint_new' and p['position'] == (2., 4., -3.) for p in changed_model['points'])
    assert changed_model['materials'][0]['diffuse'] == 'changed_break'
    assert len(changed_model['materials']) == 2
    assert changed_model['meshes'][0]['polygons'][0]['material'] == 1
    changed_illum = bpy.data.images.new('changed_break_illum', width=1, height=1)
    changed_illum.filepath = str(Path(folder) / 'changed_break_i.bmp')
    illum_node = break_mat.node_tree.nodes.new('ShaderNodeTexImage')
    illum_node.image = changed_illum
    break_mat.node_tree.links.new(illum_node.outputs['Color'], break_shader.inputs['Emission Color'])
    original_point = next(obj for obj in break_collection.objects if obj.type == 'EMPTY' and 'mod_point_index' in obj)
    bpy.data.objects.remove(original_point, do_unlink=True)
    pieces[0].data.materials.pop(index=1)
    bpy.context.view_layer.update()
    removed_break, _ = addon.prepare_break_export(bpy.context, break_collection, break_path)
    removed_model = addon.parse_model(removed_break)
    assert len(removed_model['points']) == 1 and removed_model['points'][0]['name'] == 'damagepoint_new'
    assert len(removed_model['materials']) == 1
    assert removed_model['materials'][0]['illumination'] == 'changed_break_i'
    outputs = addon.output_paths(Path(folder) / 'ship.mod', 'AUTO', True, True)
    assert outputs == {'standard': Path(folder) / 'ship.mod', 'break': Path(folder) / 'ship_brk.mod'}
    assert addon.output_paths(Path(folder) / 'ship_brk.mod', 'BREAK', True, True) == {'break': Path(folder) / 'ship_brk.mod'}
    assert addon.output_paths(Path(folder) / 'ship_brk.mod', 'STANDARD', True, True) == {'standard': Path(folder) / 'ship.mod'}
    standard_dest, break_dest = Path(folder) / 'overwrite-standard.mod', Path(folder) / 'overwrite-break.mod'
    standard_dest.write_bytes(b'old standard')
    break_dest.write_bytes(b'old break')
    snapshots = {str(p): addon.destination_snapshot(p) for p in (standard_dest, break_dest)}
    addon.write_export_outputs({standard_dest: b'new standard'}, snapshots)
    assert standard_dest.read_bytes() == b'new standard' and break_dest.read_bytes() == b'old break'
    try:
        addon.write_export_outputs({standard_dest: b'wrong'}, snapshots)
        raise AssertionError('Changed destination was overwritten')
    except ValueError:
        pass
    appeared = Path(folder) / 'appeared.mod'
    missing_snapshot = {str(appeared): addon.destination_snapshot(appeared)}
    appeared.write_bytes(b'newly appeared')
    try:
        addon.write_export_outputs({appeared: b'wrong'}, missing_snapshot)
        raise AssertionError('New destination was overwritten')
    except ValueError:
        assert appeared.read_bytes() == b'newly appeared'
    print('PASS break piece without pivot')
    pivot_strings = b'object01pivot\0hull\0hulli\0'
    pivot_material = struct.pack('<9I', 0x21, 0, 0, 0, 0, 0, 14, 0, 19)
    pivot_body = bytes(36) + chunk(b'STRS', pivot_strings) + chunk(b'PNTS', points) + chunk(b'MATS', pivot_material) + chunk(b'MOD0', geometry)
    break_path.write_bytes(b'MDLS' + struct.pack('<I', len(pivot_body)) + pivot_body)
    before = set(bpy.data.objects)
    warnings = addon.import_model(bpy.context, str(break_path))
    piece = next(o for o in set(bpy.data.objects) - before if o.type == 'MESH')
    assert piece['mod_pivot_name'] == 'object01pivot'
    assert tuple(piece.location) == (1.0, -3.0, 2.0)
    assert not any('pivot' in warning for warning in warnings)
    print('PASS numbered break pivot')
    blend_file = str(Path(folder) / 'metadata.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend_file)
    bpy.ops.wm.open_mainfile(filepath=blend_file)
    saved = bpy.data.collections['SFC MOD: ship']['mod_source_zlib_base64']
    assert zlib.decompress(base64.b64decode(saved)) == original
    print('PASS source metadata survives Blender save and reload')
