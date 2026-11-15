"""Inspect the observed SFC2-style MOD container without modifying it."""

import argparse
from collections import Counter
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


def inspect_geometry(data):
    """Decode the observed MOD0 layout, retaining unknown corner bytes."""
    if len(data) < 8:
        raise ValueError("truncated MOD0 counts")
    vertex_count, polygon_count = struct.unpack_from('<II', data)
    offset = 8
    vertices = None
    polygons = []
    unknown = []
    while offset < len(data):
        if len(data) - offset < 8:
            raise ValueError(f"truncated nested chunk at {offset}")
        tag, length = struct.unpack_from('<4sI', data, offset)
        start = offset + 8
        end = start + length
        aligned_end = (end + 3) & ~3
        if aligned_end > len(data):
            raise ValueError(f"nested chunk exceeds MOD0 at {offset}")
        payload = data[start:end]
        if tag == b'VTXS':
            if vertices is not None or length != vertex_count * 12:
                raise ValueError("invalid VTXS count or duplicate VTXS")
            vertices = list(struct.iter_unpack('<3f', payload))
        elif tag == b'POLY':
            if length < 20:
                raise ValueError("truncated POLY header")
            count, material = struct.unpack_from('<II', payload)
            if length != 20 + count * 28:
                raise ValueError("invalid POLY corner count or size")
            corners = []
            for i in range(count):
                record = payload[20 + i * 28:48 + i * 28]
                index = struct.unpack_from('<H', record)[0]
                if index >= vertex_count:
                    raise ValueError(f"vertex index {index} outside vertex array")
                corners.append({'index': index, 'uv': struct.unpack_from('<2f', record, 16), 'raw': record})
            polygons.append({'material': material, 'corners': corners, 'raw_header': payload[:20]})
        else:
            unknown.append((tag, length))
        offset = aligned_end
    if vertices is None or len(polygons) != polygon_count:
        raise ValueError("MOD0 vertex or polygon count mismatch")
    return {'vertices': vertices, 'polygons': polygons, 'unknown': unknown}


def group_break_polygons(mesh):
    groups = {}
    for polygon in mesh['polygons']:
        ids = {struct.unpack_from('<H', corner['raw'], 2)[0] for corner in polygon['corners']}
        if len(ids) != 1:
            raise ValueError('Break polygon has inconsistent piece identifiers')
        groups.setdefault(ids.pop(), []).append(polygon)
    return groups


def parse_model(data):
    chunks = inspect(data)
    def payload(tag, required=True):
        matches = [(o, n) for t, o, n in chunks if t == tag]
        if len(matches) > 1 or (required and not matches):
            raise ValueError(f'Expected one {tag!r} chunk')
        return data[matches[0][0] + 8:matches[0][0] + 8 + matches[0][1]] if matches else b''
    strings = payload(b'STRS')
    def name(offset):
        if offset >= len(strings) or b'\0' not in strings[offset:]:
            raise ValueError('Invalid string table offset')
        return strings[offset:].split(b'\0', 1)[0].decode('ascii')
    points = payload(b'PNTS', False)
    if len(points) % 16:
        raise ValueError('Invalid PNTS size')
    point_records = [{'position': (x, y, z), 'name': name(offset), 'name_offset': offset}
                     for x, y, z, offset in struct.iter_unpack('<3fI', points)]
    raw_materials = payload(b'MATS')
    materials = []
    offset = 0
    while offset < len(raw_materials):
        if len(raw_materials) - offset < 28:
            raise ValueError('Truncated material record')
        flags = struct.unpack_from('<I', raw_materials, offset)[0]
        size = 36 if flags & 0x20 else 28
        if offset + size > len(raw_materials):
            raise ValueError('Truncated material maps')
        diffuse = name(struct.unpack_from('<I', raw_materials, offset + 24)[0]) if flags & 1 else None
        illumination = name(struct.unpack_from('<I', raw_materials, offset + 32)[0]) if flags & 0x20 else None
        materials.append({'flags': flags, 'diffuse': diffuse, 'illumination': illumination,
                          'raw': raw_materials[offset:offset + size]})
        offset += size
    meshes = [inspect_geometry(data[o + 8:o + 8 + n]) for t, o, n in chunks if t == b'MOD0']
    if not meshes:
        raise ValueError('No MOD0 geometry')
    for mesh in meshes:
        for poly in mesh['polygons']:
            if len(poly['corners']) != 3:
                raise ValueError('Only triangle polygons are supported')
            if poly['material'] >= len(materials):
                raise ValueError('Polygon material index out of range')
    return {'meshes': meshes, 'points': point_records, 'materials': materials}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', action='store_true', help='inspect MOD0 geometry records')
    parser.add_argument("file", type=Path, help="MOD file to inspect")
    args = parser.parse_args()
    try:
        data = args.file.read_bytes()
        chunks = inspect(data)
        geometry = [(offset, inspect_geometry(data[offset + 8:offset + 8 + size]))
                    for tag, offset, size in chunks if tag == b'MOD0'] if args.geometry else []
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"File size: {len(data)} bytes")
    print("Tag       Offset  Payload bytes")
    for tag, offset, size in chunks:
        print(f"{tag!r}  {offset:>8}  {size:>13}")
    for offset, mesh in geometry:
        counts = dict(sorted(Counter(poly['material'] for poly in mesh['polygons']).items()))
        print(f"MOD0 at {offset}: vertices={len(mesh['vertices'])} polygons={len(mesh['polygons'])} materials={counts}")
        if mesh['unknown']:
            print(f"  unknown nested chunks: {mesh['unknown']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
