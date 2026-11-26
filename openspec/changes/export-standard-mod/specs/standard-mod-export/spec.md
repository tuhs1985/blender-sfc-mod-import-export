# Standard MOD export

## Purpose

Export supported editable standard models to MOD while preserving information needed for reliable round trips.

## ADDED Requirements

### Requirement: Write supported standard models
The exporter SHALL write all supported LODs, named points, material assignments and texture references without imposing a texture-file format.

#### Scenario: Multi-LOD model
- **WHEN** a supported three-LOD model is exported
- **THEN** the file contains three ordered LODs and their assigned materials

#### Scenario: LOD distances
- **WHEN** a standard model is exported
- **THEN** imported distances are retained, newly needed empty entries use the 100-unit baseline, and a dialog offers optional distance editing disabled by default

#### Scenario: One mesh without an LOD name
- **WHEN** a model collection contains one eligible mesh without an LOD-style name
- **THEN** it exports as a single LOD without requiring a rename

#### Scenario: Ambiguous mesh ordering
- **WHEN** a model collection contains multiple eligible meshes without a clear LOD order
- **THEN** export reports the ambiguity rather than guessing

### Requirement: Respect artist texture assignments
The exporter SHALL derive local texture stems from user-selected image names without requiring a particular image format or renaming image files.

#### Scenario: Artist-selected image name
- **WHEN** a material references an image named `thisdamntexture.bmp`
- **THEN** the exporter writes the local stem `thisdamntexture` and does not rename or convert the image

#### Scenario: Texture outside the save directory
- **WHEN** an assigned texture is outside the selected MOD save directory
- **THEN** the exporter warns the user that the game may not find it while preserving the texture assignment and allowing export

#### Scenario: Texture in the save directory
- **WHEN** an assigned texture is in the selected MOD save directory
- **THEN** the exporter writes its local reference without an outside-directory warning

### Requirement: Support new models
The exporter SHALL permit creating MOD files from newly authored Blender meshes without requiring imported source metadata. Experimental defaults and unrepresented scene data must be made clear.

#### Scenario: New single mesh
- **WHEN** the artist exports a newly created mesh
- **THEN** the exporter writes an experimental single-LOD MOD containing its triangulated geometry.

#### Scenario: Open or edited mesh
- **WHEN** an imported mesh has open edges or edited topology
- **THEN** the exporter writes its current triangles without rejecting it for the mesh's shape or completeness.

### Requirement: Report unsupported data
The exporter SHALL report changes it cannot encode rather than silently claim they were exported.

#### Scenario: Routine geometry edits
- **WHEN** vertices or topology are edited, including creating holes
- **THEN** ordinary export processing does not produce warnings merely because those edits occurred.

#### Scenario: Unavailable representation
- **WHEN** model data cannot yet be represented by the implementation
- **THEN** export reports the limitation rather than silently claiming the data was exported.

### Requirement: Preserve source data
The exporter SHALL preserve source records that have no verified editable representation when possible and report limitations when it cannot.

#### Scenario: Unchanged round trip
- **WHEN** a supported model is decoded and re-encoded without edits
- **THEN** its verified geometry and other retained records match the input

### Requirement: Development verification
The project SHALL accept MOD Viewer inspection as the user's development check and record whether a result came from the viewer or OP. The user may perform a sample OP test after the exporter is finished.

#### Scenario: Development check
- **WHEN** the user confirms an exported model in MOD Viewer
- **THEN** the result counts as the agreed development confirmation without requiring a separate OP test for that change.

#### Scenario: In-game check
- **WHEN** the user confirms an export in OP
- **THEN** that in-game confirmation supersedes a separate MOD Viewer check for the same test.
