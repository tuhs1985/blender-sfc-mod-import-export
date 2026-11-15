# Design

## Context

The existing top-level inspector checks container boundaries. The installed OP FCA and R4 importer establish a preliminary MOD0 layout; see `docs/mod0-investigation.md` for its evidence and limitations.

## Goals / Non-Goals

**Goals:** A reusable, bounded parser of all geometry chunks, retaining raw fields needed for subsequent analysis.

**Non-Goals:** Blender objects, game-coordinate conversion, inferred normals, material rendering, or MOD writing.

## Decisions

Reuse the existing Python container parser rather than coupling parsing to Blender. Parse nested chunks by declared bounded sizes and four-byte alignment. Interpret each observed 20-byte polygon header and 28-byte corner record according to the importer; preserve uninterpreted bytes, and reject inconsistent lengths, counts or indices. Report each MOD0 independently, and keep unknown nested data visible rather than inventing semantics. Test synthetic data with explicit expected values before comparing local originals.

## Risks / Trade-offs

- [Other MOD variants may differ] → Restrict claims to observed OP structures and report unsupported layouts explicitly.
- [Implicit transforms may be required] → Return raw values; no geometry orientation or UV correction is implied.
