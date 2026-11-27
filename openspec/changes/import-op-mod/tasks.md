# Tasks

## 1. Parsing

- [x] 1.1 Implement distributable bounded parsing for geometry, points and material records, verified with synthetic malformed and valid inputs.
- [x] 1.2 Verify texture resolution, missing-map warnings and material-slot preservation on the original FCA and a second model.

## 2. Blender integration

- [x] 2.1 Implement the import operator and scene creation, verifying separate LODs, names, points, UVs and material assignments in Blender background tests.
- [x] 2.2 Verify cleanup on malformed input and absent textures using Blender background tests.
- [x] 2.3 Document installation, known limitations and a fully specified example; verify installation and import with Blender.

## 3. Integration

- [x] 3.1 Run parser tests, Blender integration checks and strict OpenSpec validation; record the results.
- [x] 3.2 Group imported hardpoints and damage points into separate child collections while preserving other named points and their original order.
- [ ] 3.3 User-directed Blender check of the grouped points.
- [x] 3.4 Restore imported corner-normal directions in Blender, retaining original raw records and flat material shading; check standard and break fixtures and local OP models.
- [ ] 3.5 User-directed Blender check of imported smoothing and the v0.4.5 export-window changes.
- [x] 3.6 Provide an optional, enabled-by-default import smoothing control; verify standard and break imports and original-data preservation when disabled.
