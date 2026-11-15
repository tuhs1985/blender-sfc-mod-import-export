# Standard MOD export

## Purpose

Export supported editable standard models to MOD while preserving information needed for reliable round trips.

## ADDED Requirements

### Requirement: Write supported standard models
The exporter SHALL write all supported LODs, named points, material assignments and texture references without imposing a texture-file format.

#### Scenario: Multi-LOD model
- **WHEN** a supported three-LOD model is exported
- **THEN** the file contains three ordered LODs and their assigned materials

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
