"""Inspect the observed SFC2-style MOD container without modifying it."""

import argparse
from collections import Counter
import math
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


def write_chunk(tag, payload):
    """Serialize one observed chunk with four-byte alignment."""
    if not isinstance(tag, bytes) or len(tag) != 4:
        raise ValueError('Chunk tag must be exactly four bytes')
    if len(payload) > 0xffffffff:
        raise ValueError('Chunk payload exceeds 32-bit length')
    return tag + struct.pack('<I', len(payload)) + payload + b'\0' * (-len(payload) % 4)


def write_geometry(mesh):
    """Serialize observed geometry without silently applying unencoded edits."""
    if mesh['unknown']:
        raise ValueError('Cannot serialize unknown nested chunks safely')
    vertices = mesh['vertices']
    polygons = mesh['polygons']
    vertex_data = bytearray()
    for vertex in vertices:
        if len(vertex) != 3 or not all(math.isfinite(v) for v in vertex):
            raise ValueError('Vertex must contain three finite coordinates')
        vertex_data.extend(struct.pack('<3f', *vertex))
    output = bytearray(struct.pack('<II', len(vertices), len(polygons)))
    output.extend(write_chunk(b'VTXS', vertex_data))
    for polygon in polygons:
        header = polygon['raw_header']
        corners = polygon['corners']
        if len(header) != 20:
            raise ValueError('Invalid polygon header')
        count, _ = struct.unpack_from('<II', header)
        if count != len(corners) or not 0 <= polygon['material'] <= 0xffffffff:
            raise ValueError('Invalid polygon count or material index')
        body = bytearray(header)
        struct.pack_into('<I', body, 4, polygon['material'])
        for corner in corners:
            raw = corner['raw']
            if len(raw) != 28:
                raise ValueError('Invalid corner record')
            index = struct.unpack_from('<H', raw)[0]
            uv = corner['uv']
            if index >= len(vertices) or index != corner['index']:
                raise ValueError('Invalid or edited vertex reference')
            if len(uv) != 2 or not all(math.isfinite(v) for v in uv):
                raise ValueError('UV must contain two finite values')
            record = bytearray(raw)
            struct.pack_into('<2f', record, 16, *uv)
            body.extend(record)
        output.extend(write_chunk(b'POLY', body))
    return bytes(output)


def group_break_polygons(mesh):
    groups = {}
    for polygon in mesh['polygons']:
        ids = {struct.unpack_from('<H', corner['raw'], 2)[0] for corner in polygon['corners']}
        if len(ids) != 1:
            raise ValueError('Break polygon has inconsistent piece identifiers')
        groups.setdefault(ids.pop(), []).append(polygon)
    return groups


def rewrite_geometry(data, meshes):
    """Replace ordered geometry payloads while retaining all other source bytes."""
    chunks = inspect(data)
    if len(meshes) != sum(tag == b'MOD0' for tag, _, _ in chunks):
        raise ValueError('Geometry chunk count mismatch')
    mesh_iter = iter(meshes)
    body = bytearray(data[8:44])
    for tag, offset, size in chunks:
        end = offset + 8 + size
        aligned_end = (end + 3) & ~3
        if tag == b'MOD0':
            payload = write_geometry(next(mesh_iter))
            if len(payload) != size:
                raise ValueError('Geometry size changed; unsupported topology edit')
            body.extend(tag + struct.pack('<I', len(payload)) + payload)
            body.extend(data[end:aligned_end])
        else:
            body.extend(data[offset:aligned_end])
    return b'MDLS' + struct.pack('<I', len(body)) + body


def roundtrip_model(data):
    """Re-encode observed geometry and preserve untouched opaque top-level data."""
    meshes = [inspect_geometry(data[o + 8:o + 8 + n]) for t, o, n in inspect(data) if t == b'MOD0']
    return rewrite_geometry(data, meshes)


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


def rewrite_records(data, points, materials, meshes):
    """Rewrite verified point and existing texture fields, preserving opaque records."""
    original = parse_model(data)
    if len(points) != len(original['points']) or len(materials) != len(original['materials']):
        raise ValueError('Adding or removing points or materials is not supported')
    for mesh in meshes:
        for polygon in mesh['polygons']:
            if not 0 <= polygon['material'] < len(materials):
                raise ValueError('Polygon material index out of range')
    geometry_data = rewrite_geometry(data, meshes)
    chunks = inspect(geometry_data)
    def get(tag):
        found = [(o, n) for t, o, n in chunks if t == tag]
        return geometry_data[found[0][0] + 8:found[0][0] + 8 + found[0][1]] if found else b''
    strings = bytearray(get(b'STRS'))
    def assign_name(value, previous, old_offset):
        if value == previous:
            return old_offset
        if not isinstance(value, str) or not value or '\0' in value:
            raise ValueError('Invalid string reference')
        try:
            encoded = value.encode('ascii') + b'\0'
        except UnicodeEncodeError as exc:
            raise ValueError('Non-ASCII string references are not supported') from exc
        offset = len(strings)
        strings.extend(encoded)
        return offset
    point_data = bytearray()
    for point, prior in zip(points, original['points']):
        xyz = point['position']
        if len(xyz) != 3 or not all(math.isfinite(v) for v in xyz):
            raise ValueError('Point must contain three finite coordinates')
        offset = assign_name(point['name'], prior['name'], prior['name_offset'])
        point_data.extend(struct.pack('<3fI', *xyz, offset))
    material_data = bytearray()
    for material, prior in zip(materials, original['materials']):
        if material['flags'] != prior['flags'] or material['raw'] != prior['raw']:
            raise ValueError('Editing material flags or opaque records is not supported')
        raw = bytearray(prior['raw'])
        for field, field_offset in (('diffuse', 24), ('illumination', 32)):
            current, previous = material[field], prior[field]
            if previous is None:
                if current is not None:
                    raise ValueError(f'Adding a {field} map is not supported yet')
            else:
                old_offset = struct.unpack_from('<I', raw, field_offset)[0]
                new_offset = assign_name(current, previous, old_offset)
                struct.pack_into('<I', raw, field_offset, new_offset)
        material_data.extend(raw)
    replacements = {b'STRS': bytes(strings), b'PNTS': bytes(point_data), b'MATS': bytes(material_data)}
    body = bytearray(geometry_data[8:44])
    for tag, offset, size in chunks:
        end = offset + 8 + size
        aligned = (end + 3) & ~3
        replacement = replacements.get(tag)
        if replacement is None or replacement == geometry_data[offset + 8:end]:
            body.extend(geometry_data[offset:aligned])
        else:
            body.extend(write_chunk(tag, replacement))
    return b'MDLS' + struct.pack('<I', len(body)) + body


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
