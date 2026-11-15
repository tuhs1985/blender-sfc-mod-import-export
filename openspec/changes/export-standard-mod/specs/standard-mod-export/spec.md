# Standard MOD export

## Purpose

Export supported editable standard models to MOD while preserving information needed for reliable round trips.

## ADDED Requirements

### Requirement: Write supported standard models
The exporter SHALL write all supported LODs, named points, material assignments and texture references without imposing a texture-file format.

#### Scenario: Multi-LOD model
- **WHEN** a supported three-LOD model is exported
- **THEN** the file contains three ordered LODs and their assigned materials

#### Scenario: One mesh without an LOD name
- **WHEN** a model collection contains one eligible mesh without an LOD-style name
- **THEN** it exports as a single LOD without requiring a rename

#### Scenario: Ambiguous mesh ordering
- **WHEN** a model collection contains multiple eligible meshes without a clear LOD order
- **THEN** export reports the ambiguity rather than guessing

### Requirement: Respect artist texture assignments
The exporter SHALL preserve user-selected texture references without requiring a particular image format or renaming textures.

#### Scenario: Artist-selected image name
- **WHEN** a material references an image named `thisdamntexture.bmp`
- **THEN** the exporter preserves that reference rather than enforcing a naming pattern

#### Scenario: Texture outside the save directory
- **WHEN** an assigned texture is outside the selected MOD save directory
- **THEN** the exporter warns the user that the game may not find it while preserving the texture assignment and allowing export

#### Scenario: Texture in the save directory
- **WHEN** an assigned texture is in the selected MOD save directory
- **THEN** the exporter writes its local reference without an outside-directory warning

### Requirement: Refuse unsafe export
The exporter SHALL reject unsupported edits and malformed or missing required data rather than silently produce an incomplete model.

#### Scenario: Missing source metadata
- **WHEN** a model requires source metadata that is unavailable
- **THEN** export reports an error and does not overwrite the destination

### Requirement: Preserve source data
The exporter SHALL preserve source records that have no verified editable representation when possible and report limitations when it cannot.

#### Scenario: Unchanged round trip
- **WHEN** a supported model is decoded and re-encoded without edits
- **THEN** its verified geometry and other retained records match the input
