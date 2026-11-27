## ADDED Requirements

### Requirement: Select smoothing in export browser
The exporter SHALL offer current export behavior, direct Blender corner normals, and splitting at Blender shading boundaries in the export file browser.

#### Scenario: Option disabled
- **WHEN** current export behavior is selected
- **THEN** existing export behavior and source geometry are unchanged.

#### Scenario: Option enabled
- **WHEN** a standard or break model is exported with direct normals or split boundaries enabled
- **THEN** the operation uses temporary geometry and does not alter the editable Blender mesh.
- **AND** faces, UVs, materials and break-piece identifiers are retained.

#### Scenario: Blender smoothing
- **WHEN** an evaluated mesh has a sharp edge or discontinuous evaluated corner normal directions
- **THEN** the corresponding shared edge is split on the exported mesh, and normals are regenerated using the exporter method.

#### Scenario: Direct normals
- **WHEN** direct normals are selected
- **THEN** evaluated Blender corner normal directions are transformed and written to the MOD without splitting shared vertices.
