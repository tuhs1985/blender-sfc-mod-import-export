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
- **THEN** an empty is created with the corresponding name and transformed position

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
