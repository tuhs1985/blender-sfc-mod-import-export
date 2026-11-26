# Tasks

## 1. Binary foundation

- [x] 1.1 Implement bounded chunk and geometry serialization with synthetic round-trip and invalid-input tests.
- [x] 1.2 Verify all three original FCA geometry chunks re-encode byte-for-byte, without committing assets.

## 2. Lossless model representation

- [x] 2.1 Preserve source header, chunk, string, point and material metadata through Blender import; test reload and exact unchanged reconstruction.
- [x] 2.2 Expand encoding of mesh, UV, material-reference and point edits with focused tests, without judging mesh quality or silently discarding edits.

## 3. Blender export and integration

- [x] 3.1 Add a safe standard MOD export operator that validates before writing and protects existing destinations; test success and failure in Blender.
- [ ] 3.2 Run the relevant synthetic and original FCA round-trip tests, document limitations, and use MOD Viewer for user-directed development checks.

## 4. Experimental editing workflow

- [x] 4.1 Allow renamed LOD objects and warn about colliding texture stems instead of blocking export.
- [x] 4.1a Encode vertex-position edits with experimental old-plugin-style normal recalculation; verify with synthetic and Blender tests.
- [x] 4.1b Export a new selected mesh as an experimental single-LOD MOD without imported source metadata; test Blender export and re-import.
- [x] 4.1d Encode edited topology, including open meshes, without checking whether the model is watertight; test Blender export and re-import.
- [x] 4.1e Do not warn about routine vertex and topology edits; retain actionable export warnings.
- [x] 4.1f Implement authored LOD, point and diffuse/illumination export; verify synthetic Blender export and re-import.
- [x] 4.1g Prevent protected-folder temporary-file creation from retrying permission errors indefinitely; report the destination error and test in Blender.
- [ ] 4.1c Complete validation of authored LODs, point markers and illumination maps using MOD Viewer or an in-game test; an in-game test supersedes a separate viewer check for the same test.
- [ ] 4.2 Encode experimental mesh and other edits that are currently rejected, preserving the user's changes and reporting any that cannot yet be represented. Validate each edit with controlled tests; avoid silently writing the original data in place of edits.
- [ ] 4.3 When the exporter is finished, prepare a sample for the user's optional OP test; record actual viewer and game results separately.

## 5. Review findings

- [x] 5.1 Export correctly named LODs added to imported models instead of silently omitting them; support removing LODs and preserve correct ordering.
- [x] 5.2 Find connected material shaders without relying on their display names; preserve texture assignments and report images with no usable file reference.
- [x] 5.3 Investigate and update derived size metadata when geometry changes; retain unchanged source values for unchanged models.
- [x] 5.4 Support standard-model transforms, evaluated geometry, and models without UV layers without judging mesh quality; allow the full 65,536-vertex index range.
- [ ] 5.5 Investigate non-ASCII string encoding and verify transition-distance behavior for newly added LODs in MOD Viewer or OP.
- [x] 5.6 Preserve imported LOD distances, initialize new distances using D4v1ks' 100-unit baseline, and offer an opt-in export dialog for editing them; verify serialization and Blender integration.
- [ ] 5.7 Verify edited and newly initialized LOD transition behavior in MOD Viewer or OP.
