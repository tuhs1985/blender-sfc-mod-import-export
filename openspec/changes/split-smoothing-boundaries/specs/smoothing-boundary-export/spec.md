## ADDED Requirements

### Requirement: Optional smoothing boundary preparation
The exporter SHALL allow the user to opt into splitting at Blender shading boundaries or at an angle threshold on the exported geometry.

#### Scenario: Option disabled
- **WHEN** split by angle is not enabled
- **THEN** existing export behavior and source geometry are unchanged.

#### Scenario: Option enabled
- **WHEN** a standard or break model is exported with Blender smoothing or split by angle enabled
- **THEN** the operation uses temporary geometry and does not alter the editable Blender mesh.
- **AND** faces, UVs, materials and break-piece identifiers are retained.

#### Scenario: Blender smoothing
- **WHEN** an evaluated mesh has a sharp edge or discontinuous evaluated corner normal directions
- **THEN** the corresponding shared edge is split on the exported mesh, and normals are regenerated using the exporter method.
