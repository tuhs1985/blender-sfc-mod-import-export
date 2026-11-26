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
    def test_lod_distances_preserve_source_and_fill_new_entries(self):
        data = b'MDLS' + struct.pack('<I', 36) + struct.pack('<IfI6f', 512, 1., 3, 5., 0., 180., 350., 0., 0.)
        extended = fmt.update_lod_distances(data, old_count=3, new_count=5)
        self.assertEqual(struct.unpack_from('<5f', extended, 24), (0., 180., 350., 450., 550.))
        self.assertEqual(fmt.update_lod_distances(data, old_count=3, new_count=3), data)
        changed = fmt.update_lod_distances(data, distances=(0., 50., 150., 250., 450.))
        self.assertEqual(struct.unpack_from('<5f', changed, 24), (0., 50., 150., 250., 450.))

    def test_break_pieces_keep_ids_and_separate_vertex_indices(self):
        first = fmt.inspect_geometry(self.geometry())
        second = fmt.inspect_geometry(self.geometry())
        combined = fmt.combine_break_geometry([(0, first), (4, second)])
        parsed = fmt.inspect_geometry(fmt.write_geometry(combined))
        groups = fmt.group_break_polygons(parsed)
        self.assertEqual(sorted(groups), [0, 4])
        self.assertEqual([c['index'] for c in groups[4][0]['corners']], [3, 4, 5])

    def test_detects_distinct_images_that_share_local_stem(self):
        conflicts = fmt.texture_stem_collisions([r'C:\one\Hull.png', r'C:\two\hull.bmp', r'C:\ONE\HULL.PNG', r'C:\two\other.png'])
        self.assertEqual(set(conflicts), {'hull'})
        self.assertEqual(len(conflicts['hull']), 2)

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

    def test_writes_vertex_edits_and_recalculates_normals(self):
        geometry = self.geometry()
        body = bytes(36) + chunk(b'MOD0', geometry)
        data = b'MDLS' + struct.pack('<I', len(body)) + body
        mesh = fmt.inspect_geometry(geometry)
        mesh['vertices'][2] = (0., 1., 1.)
        output = fmt.rewrite_geometry(data, [mesh])
        self.assertAlmostEqual(struct.unpack_from('<f', output, 12)[0], 2 ** 0.5, places=6)
        result = fmt.inspect_geometry(output[52:])
        self.assertEqual(result['vertices'][2], (0., 1., 1.))
        normal = struct.unpack_from('<3f', result['polygons'][0]['raw_header'], 8)
        self.assertAlmostEqual(normal[1], 2 ** -0.5, places=6)
        self.assertAlmostEqual(normal[2], -(2 ** -0.5), places=6)
        for corner in result['polygons'][0]['corners']:
            self.assertEqual(struct.unpack_from('<3f', corner['raw'], 4), normal)

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
        model['materials'][0]['diffuse'] = r'C:\outside\thisdamntexture.png'
        model['meshes'][0]['polygons'][0]['material'] = 0
        out = fmt.rewrite_records(data, model['points'], model['materials'], model['meshes'])
        parsed = fmt.parse_model(out)
        self.assertEqual(parsed['points'][0]['position'], (4., 5., 6.))
        self.assertEqual(parsed['materials'][0]['diffuse'], 'thisdamntexture')
        self.assertEqual(parsed['materials'][0]['illumination'], 'hulli')
        model['meshes'][0]['polygons'][0]['material'] = 1
        with self.assertRaises(ValueError):
            fmt.rewrite_records(data, model['points'], model['materials'], model['meshes'])
        model['meshes'][0]['polygons'][0]['material'] = 0
        model['materials'][0]['illumination'] = None
        with self.assertRaises(ValueError):
            fmt.rewrite_records(data, model['points'], model['materials'], model['meshes'])
