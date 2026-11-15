import importlib.util
import struct
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location('mod_format', Path(__file__).resolve().parents[1] / 'addon' / 'io_scene_sfc_mod' / 'mod_format.py')
fmt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmt)


def chunk(tag, body):
    return tag + struct.pack('<I', len(body)) + body + b'\0' * (-len(body) % 4)


class WriterTests(unittest.TestCase):
    def geometry(self):
        vertices = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
        corners = b''.join(struct.pack('<I3f2fI', i, 0, 0, 1, i / 2, 0, 0) for i in range(3))
        poly = struct.pack('<II3f', 3, 4, 0, 0, 1) + corners
        return struct.pack('<II', 3, 1) + chunk(b'VTXS', vertices) + chunk(b'POLY', poly)

    def test_round_trip_preserves_geometry(self):
        data = self.geometry()
        self.assertEqual(fmt.write_geometry(fmt.inspect_geometry(data)), data)

    def test_rejects_index_edits_not_yet_encoded(self):
        mesh = fmt.inspect_geometry(self.geometry())
        mesh['polygons'][0]['corners'][0]['index'] = 2
        with self.assertRaises(ValueError):
            fmt.write_geometry(mesh)

    def test_encodes_uv_and_material_edits(self):
        mesh = fmt.inspect_geometry(self.geometry())
        mesh['polygons'][0]['material'] = 7
        mesh['polygons'][0]['corners'][0]['uv'] = (0.5, 0.25)
        result = fmt.inspect_geometry(fmt.write_geometry(mesh))
        self.assertEqual(result['polygons'][0]['material'], 7)
        self.assertEqual(result['polygons'][0]['corners'][0]['uv'], (0.5, 0.25))

    def test_round_trip_preserves_opaque_chunks_and_padding(self):
        opaque = b'EXTR' + struct.pack('<I', 1) + b'a\x11\x22\x33'
        body = bytes(range(36)) + opaque + chunk(b'MOD0', self.geometry())
        data = b'MDLS' + struct.pack('<I', len(body)) + body
        self.assertEqual(fmt.roundtrip_model(data), data)

    def test_rewrites_uv_without_changing_other_chunks(self):
        other = chunk(b'EXTR', b'keep')
        body = bytes(36) + other + chunk(b'MOD0', self.geometry())
        data = b'MDLS' + struct.pack('<I', len(body)) + body
        mesh = fmt.inspect_geometry(self.geometry())
        mesh['polygons'][0]['corners'][0]['uv'] = (0.5, 0.25)
        output = fmt.rewrite_geometry(data, [mesh])
        self.assertEqual(output[44:44 + len(other)], other)
        self.assertEqual(fmt.inspect_geometry(output[64:])['polygons'][0]['corners'][0]['uv'], (0.5, 0.25))

    def test_rejects_geometry_count_mismatch(self):
        body = bytes(36) + chunk(b'MOD0', self.geometry())
        data = b'MDLS' + struct.pack('<I', len(body)) + body
        with self.assertRaises(ValueError):
            fmt.rewrite_geometry(data, [])

    def test_rejects_unserializable_nested_chunks(self):
        mesh = fmt.inspect_geometry(self.geometry())
        mesh['unknown'] = [(b'ZZZZ', 2)]
        with self.assertRaises(ValueError):
            fmt.write_geometry(mesh)

    def test_update_point_and_texture_reference_without_format_restriction(self):
        strings = b'hardpoint1\0hull\0hulli\0'
        points = struct.pack('<3fI', 1, 2, 3, 0)
        material = struct.pack('<9I', 0x21, 0, 0, 0, 0, 0, 11, 0, 16)
        geometry = bytearray(self.geometry())
        struct.pack_into('<I', geometry, 64, 0)
        body = bytes(36) + chunk(b'STRS', strings) + chunk(b'PNTS', points) + chunk(b'MATS', material) + chunk(b'MOD0', geometry)
        data = b'MDLS' + struct.pack('<I', len(body)) + body
        model = fmt.parse_model(data)
        model['points'][0]['position'] = (4., 5., 6.)
        model['materials'][0]['diffuse'] = 'hull.png'
        model['meshes'][0]['polygons'][0]['material'] = 0
        out = fmt.rewrite_records(data, model['points'], model['materials'], model['meshes'])
        parsed = fmt.parse_model(out)
        self.assertEqual(parsed['points'][0]['position'], (4., 5., 6.))
        self.assertEqual(parsed['materials'][0]['diffuse'], 'hull.png')
        self.assertEqual(parsed['materials'][0]['illumination'], 'hulli')
        model['meshes'][0]['polygons'][0]['material'] = 1
        with self.assertRaises(ValueError):
            fmt.rewrite_records(data, model['points'], model['materials'], model['meshes'])
        model['meshes'][0]['polygons'][0]['material'] = 0
        model['materials'][0]['illumination'] = None
        with self.assertRaises(ValueError):
            fmt.rewrite_records(data, model['points'], model['materials'], model['meshes'])
