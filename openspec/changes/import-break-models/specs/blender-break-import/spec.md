# Break-model import

## Purpose

Enable artists to inspect and edit OP destruction-model pieces in Blender.

## ADDED Requirements

### Requirement: Separate break pieces
The importer SHALL create a separate mesh for each supported piece identifier while retaining polygon order, material assignments and stored UVs.

#### Scenario: Seven-piece model
- **WHEN** a break model contains seven valid piece identifiers
- **THEN** Blender receives seven distinct piece objects with all polygons represented

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
