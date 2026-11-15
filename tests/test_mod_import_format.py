import importlib.util
import struct
import unittest
from pathlib import Path


class ImportFormatTests(unittest.TestCase):
    def test_named_point_and_material_slots(self):
        spec = importlib.util.spec_from_file_location('mod_format', Path(__file__).resolve().parents[1] / 'addon' / 'io_scene_sfc_mod' / 'mod_format.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def chunk(tag, data):
            return tag + struct.pack('<I', len(data)) + data + b'\0' * (-len(data) % 4)
        strings = b'hardpoint1\0hull\0hulli\0'
        material = struct.pack('<9I', 0x21, 0, 0, 0, 0, 0, 11, 0, 16)
        points = struct.pack('<3fI', 1, 2, 3, 0)
        vertices = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
        corners = b''.join(struct.pack('<I3f2fI', i, 0, 0, 1, 0, 0, 0) for i in range(3))
        geometry = struct.pack('<II', 3, 1) + chunk(b'VTXS', vertices) + chunk(b'POLY', struct.pack('<II3f', 3, 0, 0, 0, 1) + corners)
        body = bytes(36) + chunk(b'STRS', strings) + chunk(b'PNTS', points) + chunk(b'MATS', material) + chunk(b'MOD0', geometry)
        result = module.parse_model(b'MDLS' + struct.pack('<I', len(body)) + body)
        self.assertEqual(result['points'][0]['name'], 'hardpoint1')
        self.assertEqual(result['points'][0]['position'], (1., 2., 3.))
        self.assertEqual(result['materials'][0]['diffuse'], 'hull')
        self.assertEqual(result['materials'][0]['illumination'], 'hulli')
        self.assertEqual(len(result['meshes'][0]['polygons']), 1)
