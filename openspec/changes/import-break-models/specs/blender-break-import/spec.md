# Break-model import

## Purpose

Enable artists to inspect and edit OP destruction-model pieces in Blender.

## ADDED Requirements

### Requirement: Separate break pieces
The importer SHALL create a separate mesh for each supported piece identifier while retaining polygon order, material assignments and stored UVs. For a file named `<shipname>_brk.mod`, piece IDs 0, 1, and 2 SHALL be named `<shipname>_brk_1`, `<shipname>_brk_2`, and `<shipname>_brk_3` in an empty namespace, retaining the original zero-based ID as metadata.

#### Scenario: Seven-piece model
- **WHEN** a break model contains seven valid piece identifiers
- **THEN** Blender receives seven distinct piece objects named `<shipname>_brk_1` through `<shipname>_brk_7` with all polygons represented

#### Scenario: Stored smoothing on break pieces
- **WHEN** a break piece contains stored corner normals
- **THEN** its Blender mesh displays their representable directions without welding the piece's vertices.

### Requirement: Handle pivot records
The importer SHALL position a piece origin at a matching numbered pivot when unambiguous, and SHALL NOT warn when pivot records are absent.

#### Scenario: No pivots in source
- **WHEN** a valid break model has no pivot records
- **THEN** the pieces import in place without a missing-pivot warning

### Requirement: Reject ambiguous grouping
The importer SHALL reject a polygon whose corner piece identifiers disagree without leaving partial model objects.

#### Scenario: Mixed piece identifiers
- **WHEN** a polygon's corners indicate different piece IDs
- **THEN** the importer reports an error and creates no model objects
