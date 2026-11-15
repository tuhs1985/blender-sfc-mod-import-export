import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "inspect_mod.py"


def container(chunks=b""):
    body = bytes(36) + chunks
    return b"MDLS" + struct.pack("<I", len(body)) + body


class InspectorTests(unittest.TestCase):
    def run_inspector(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.mod"
            path.write_bytes(data)
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(path.read_bytes(), data)
            return result

    def test_reports_unknown_chunk_and_alignment(self):
        result = self.run_inspector(container(b"ABCD\x03\x00\x00\x00abc\0" + b"MOD0\x00\x00\x00\x00"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ABCD", result.stdout)
        self.assertIn("44", result.stdout)
        self.assertIn("MOD0", result.stdout)
        self.assertIn("56", result.stdout)

    def test_rejects_malformed_files(self):
        cases = [b"", b"BAD!" + bytes(40), container()[:-1], container(b"ABC"),
                 container(b"TEST\x04\x00\x00\x00ab"),
                 container(b"TEST\x01\x00\x00\x00a")]
        for data in cases:
            with self.subTest(data=data):
                result = self.run_inspector(data)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
