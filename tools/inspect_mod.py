"""Inspect the observed SFC2-style MOD container without modifying it."""

import argparse
import struct
import sys
from pathlib import Path


def inspect(data):
    if len(data) < 44:
        raise ValueError("file is shorter than the 44-byte container header")
    if data[:4] != b"MDLS":
        raise ValueError("missing MDLS signature")
    size = struct.unpack_from("<I", data, 4)[0]
    if size != len(data) - 8:
        raise ValueError("container length does not match file size")
    offset = 44
    chunks = []
    while offset < len(data):
        if len(data) - offset < 8:
            raise ValueError(f"truncated chunk header at offset {offset}")
        tag = data[offset:offset + 4]
        length = struct.unpack_from("<I", data, offset + 4)[0]
        end = offset + 8 + length
        if end > len(data):
            raise ValueError(f"chunk payload at offset {offset} exceeds container")
        aligned_end = (end + 3) & ~3
        if aligned_end > len(data):
            raise ValueError(f"missing chunk alignment padding at offset {offset}")
        chunks.append((tag, offset, length))
        offset = aligned_end
    return chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="MOD file to inspect")
    args = parser.parse_args()
    try:
        data = args.file.read_bytes()
        chunks = inspect(data)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"File size: {len(data)} bytes")
    print("Tag       Offset  Payload bytes")
    for tag, offset, size in chunks:
        print(f"{tag!r}  {offset:>8}  {size:>13}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
