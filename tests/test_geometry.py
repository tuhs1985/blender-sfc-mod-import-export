import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_mod import inspect_geometry


def chunk(tag, payload):
    return tag + struct.pack('<I', len(payload)) + payload + b'\0' * (-len(payload) % 4)


def model(index=2):
    vertices = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
    corners = b''.join(struct.pack('<I3f2fI', i, 0, 0, 1, u, v, 0)
                       for i, u, v in [(0, 0, 0), (1, 1, 0), (index, 0, 1)])
    poly = struct.pack('<II3f', 3, 7, 0, 0, 1) + corners
    return struct.pack('<II', 3, 1) + chunk(b'VTXS', vertices) + chunk(b'POLY', poly)


class GeometryTests(unittest.TestCase):
    def test_triangle_preserves_indices_and_uvs(self):
        result = inspect_geometry(model())
        self.assertEqual(len(result['vertices']), 3)
        polygon = result['polygons'][0]
        self.assertEqual(polygon['material'], 7)
        self.assertEqual([c['index'] for c in polygon['corners']], [0, 1, 2])
        self.assertEqual([c['uv'] for c in polygon['corners']], [(0., 0.), (1., 0.), (0., 1.)])

    def test_rejects_out_of_range_index_and_truncation(self):
        for data in (model(3), model()[:-1]):
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                inspect_geometry(data)

    def test_cli_reports_each_geometry_chunk_without_modifying_input(self):
        data = chunk(b'MDLS', bytes(36) + chunk(b'MOD0', model()) * 2)
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'model.mod'
            file.write_bytes(data)
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'tools' / 'inspect_mod.py'), '--geometry', str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count('vertices=3 polygons=1'), 2)
            self.assertIn('7: 1', result.stdout)
            self.assertEqual(file.read_bytes(), data)
