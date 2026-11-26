# Break export

## ADDED Requirements

### Requirement: Select output mode
The export file browser SHALL offer Auto, Standard Model Only, and Break Model Only in a dropdown, with Auto selected by default and concise instructions in the right panel. Auto writes both model types present in the selected model collection; a single available type produces one output.

#### Scenario: Both model types
- **WHEN** Auto is selected and standard LODs and break pieces are present
- **THEN** export the standard MOD and the separate `_brk.mod` file.

### Requirement: Preserve break pieces
The exporter SHALL encode each break piece's zero-based numeric ID, geometry, material references and UVs without requiring pivot points.

#### Scenario: Named new break pieces
- **WHEN** an authored break piece is named `fca_brk_1`
- **THEN** its polygons use break piece ID zero.

#### Scenario: Empty break objects
- **WHEN** break objects have no evaluated faces and other pieces contain faces
- **THEN** export the non-empty pieces, preserve their numeric IDs and report the skipped objects without blocking the export.

#### Scenario: Entire break model is empty
- **WHEN** Auto export finds only empty break objects alongside a standard model
- **THEN** export the standard model, report the skipped break objects and leave any existing break file untouched.

### Requirement: Explicit overwrite selection
The exporter SHALL ask before replacing existing output files, showing a checked-by-default checkbox for each existing file. Unchecked files SHALL remain untouched; cancellation SHALL write no outputs. Files that appear or change after confirmation SHALL not be silently replaced.

#### Scenario: Skip one existing output
- **WHEN** both outputs exist and the user unchecks the break file
- **THEN** only the standard file is replaced.
