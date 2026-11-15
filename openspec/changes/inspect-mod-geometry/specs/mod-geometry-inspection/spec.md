# Geometry inspection

## Purpose

Enable inspection of observed Orion Pirates model geometry as groundwork for a Blender importer.

## ADDED Requirements

### Requirement: Inspect each geometry chunk
The inspector SHALL expose each observed MOD0 geometry chunk in file order, including vertex and polygon counts and polygon material indices.

#### Scenario: Multiple LOD chunks
- **WHEN** a valid model contains three MOD0 chunks
- **THEN** the inspector reports all three chunks and their individual counts

### Requirement: Decode corner references
The inspector SHALL expose each polygon's vertex references and stored UV values without applying coordinate or UV conversion.

#### Scenario: Triangle with distinct UVs
- **WHEN** a polygon contains three valid corners with distinct stored UVs
- **THEN** inspection preserves their order, vertex references and UV values

### Requirement: Reject inconsistent geometry
The inspector SHALL reject truncated nested chunks, inconsistent declared counts and vertex references outside their vertex array.

#### Scenario: Out-of-range vertex index
- **WHEN** a corner references a vertex beyond the declared vertex array
- **THEN** inspection fails with an actionable error
