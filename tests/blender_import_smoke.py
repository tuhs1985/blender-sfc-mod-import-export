"""Run with Blender's --background --factory-startup --python option."""
import struct
import sys
import tempfile
from pathlib import Path
import bpy

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / 'addon'))
import io_scene_sfc_mod as addon
assert addon.bl_info['name'] == 'Starfleet Command 1/2/OP/3 MOD Import'

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
    path.write_bytes(b'MDLS' + struct.pack('<I', len(body)) + body)
    before = set(bpy.data.objects)
    warnings = addon.import_model(bpy.context, str(path))
    created = set(bpy.data.objects) - before
    assert len(warnings) == 2
    assert sorted(o.type for o in created) == ['EMPTY', 'MESH']
    assert next(o for o in created if o.type == 'EMPTY')['mod_name'] == 'hardpoint1'
    assert len(next(o for o in created if o.type == 'MESH').data.materials) == 1
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
