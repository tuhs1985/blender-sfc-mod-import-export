"""Run with Blender's --background --factory-startup --python option."""
import struct
import base64
import zlib
import sys
import tempfile
from pathlib import Path
import bpy

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / 'addon'))
import io_scene_sfc_mod as addon
assert addon.bl_info['name'] == 'Starfleet Command 1/2/OP/3 MOD Import/Export'
addon.register()

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
    try:
        addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
        raise AssertionError('Unsupported material edit was accepted')
    except ValueError:
        pass
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
    try:
        addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
        raise AssertionError('Unsupported point rotation was accepted')
    except ValueError:
        pass
    point.rotation_euler.x = 0.0
    exported, export_warnings = addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
    model = addon.parse_model(exported)
    assert model['points'][0]['position'] == (4., 5., 6.)
    assert model['meshes'][0]['polygons'][0]['corners'][1]['uv'] == (0.5, 0.25)
    exported_mesh.data.vertices[0].co.x += 0.000001
    try:
        addon.prepare_standard_export(imported_collection, Path(folder) / 'export.mod')
        raise AssertionError('Unsupported vertex edit was accepted')
    except ValueError:
        pass
    try:
        result = bpy.ops.export_scene.sfc_mod(filepath=str(target))
        assert result == {'CANCELLED'}
    except RuntimeError:
        pass
    assert target.read_bytes() == original
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
    exported, _ = addon.prepare_standard_export(imported.users_collection[0], Path(folder) / 'ship.mod')
    assert addon.parse_model(exported)['materials'][0]['diffuse'] == 'thisdamntexture'
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
