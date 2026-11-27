# Blender MOD import

## Purpose

Allow artists to bring supported Orion Pirates models into Blender for inspection and editing.

## ADDED Requirements

### Requirement: Import LOD meshes
The importer SHALL create a separate mesh for each supported MOD0 chunk, preserving stored polygon order, material associations and UVs while applying the established FCA orientation and winding.

#### Scenario: Three LODs
- **WHEN** a supported model has three MOD0 chunks
- **THEN** Blender receives three separate mesh objects in file order

### Requirement: Import point markers
The importer SHALL represent valid named points as Blender empties with original coordinates and names preserved.

#### Scenario: Hardpoint present
- **WHEN** a valid model contains a named hardpoint
- **THEN** an empty is created with the corresponding name and transformed position in a HardPoints child collection

#### Scenario: Damage point present
- **WHEN** a valid model contains an `a1` through `f`-series damage point
- **THEN** its empty is placed in a DamagePoints child collection; other named points remain directly in the model collection

### Requirement: Display imported smoothing
The importer SHALL offer an enabled-by-default Import Smoothing option that applies stored corner-normal directions to Blender's mesh shading while retaining source records for unchanged exports.

#### Scenario: Import smoothing disabled
- **WHEN** Import Smoothing is disabled for a standard or break model
- **THEN** the imported mesh displays flat faces without custom normals, while original records remain available for unchanged standard export.

#### Scenario: Shared vertex with different corner normals
- **WHEN** adjacent smooth faces share a vertex but carry different normal directions
- **THEN** Blender displays the stored directions without welding or detaching vertices.

#### Scenario: Zero or non-unit normal
- **WHEN** a stored normal is zero or non-unit length
- **THEN** Blender may normalize or choose an automatic display direction, while the original record remains available for unchanged standard export.

### Requirement: Preserve material slots
The importer SHALL preserve material table order and assign polygon material indices without discarding early or unused slots.

#### Scenario: First slots used
- **WHEN** polygons use material slots 1 and 2
- **THEN** those polygons retain the corresponding material assignments

### Requirement: Connect texture maps
The importer SHALL use available diffuse and illumination images as separate nodes in the same material without restricting them to BMP. It SHALL preserve references and allow unresolved, ambiguous, or unreadable images without rejecting the model.

#### Scenario: Missing illumination image
- **WHEN** a referenced illumination map is absent
- **THEN** the model still imports and the user receives a warning

#### Scenario: Alternate image format
- **WHEN** a texture stem uniquely matches a Blender-supported PNG image
- **THEN** the importer loads that image without requiring a BMP

#### Scenario: Ambiguous image stem
- **WHEN** a texture stem matches more than one supported image
- **THEN** the importer retains the reference and reports the ambiguity without selecting one arbitrarily

### Requirement: Reject malformed input
The importer SHALL report invalid structure without leaving partially created scene objects.

#### Scenario: Bad vertex reference
- **WHEN** a polygon references a nonexistent vertex
- **THEN** the import fails and creates no model objects
