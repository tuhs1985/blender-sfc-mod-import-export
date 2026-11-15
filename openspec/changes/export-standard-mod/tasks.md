# Tasks

## 1. Binary foundation

- [x] 1.1 Implement bounded chunk and geometry serialization with synthetic round-trip and invalid-input tests.
- [x] 1.2 Verify all three original FCA geometry chunks re-encode byte-for-byte, without committing assets.

## 2. Lossless model representation

- [x] 2.1 Preserve source header, chunk, string, point and material metadata through Blender import; test reload and exact unchanged reconstruction.
- [ ] 2.2 Encode verified mesh, UV, material-reference and point edits; reject unsupported topology and unverified edits with focused tests.

## 3. Blender export and integration

- [ ] 3.1 Add a safe standard MOD export operator that validates before writing and protects existing destinations; test success and failure in Blender.
- [ ] 3.2 Run full synthetic and original FCA round-trip tests, document limitations, and prepare for user-directed OP validation.
