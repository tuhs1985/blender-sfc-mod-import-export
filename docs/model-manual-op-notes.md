# Model manual: Orion Pirates research notes

Target: Starfleet Command: Orion Pirates (OP). The supplied `ModelManual.pdf` is a 46-page SFC III modeling manual, so its SFC3-specific instructions must not be treated as OP requirements. The PDF remains in the user's reference materials and is not distributed in this repository.

## Useful context

- **Geometry and compatibility (PDF pages 2, 5):** The manual describes MOD geometry as compatible across SFC generations, while warning that later texturing features can cause trouble with earlier games. This is the manual's broad claim, not proof that every MOD variant or feature works in OP; verify against OP models and the game.
- **Static LODs (page 8):** The manual says earlier SFC versions used multiple versions of a ship in one MOD, typically three levels of detail. SFC3 instead introduced dynamic LOD and generally uses one model. OP's actual layout, number of LODs, distances, and edge cases must be established from OP files and the SFC II plugin, not assumed from this general description.
- **Original SFC II plugin (pages 27–28):** At the time of the manual, its author says the unmodified SFC II Max plugin was used for SFC I, II, and III. The page 28 instruction to select break-model mode for ordinary models is explicitly for SFC III; it is not an OP export rule. The supplied plugin readme instead describes standard multiple-LOD and separate break-model export modes for SFC II.
- **Hardpoints (page 14):** The manual says SFC I/II weapon hardpoint numbers were associated with tactical data in the specfile; the SFC3 primary/heavy number split is a later rule and is not an OP requirement. Preserve names and positions and verify OP behavior.
- **Damage points (pages 15–16):** The manual describes named dummy objects arranged in lettered groups around the ship for visual impact placement. Its six groups of three are useful evidence to investigate, not yet a validated universal OP requirement.
- **Break models (pages 7–8, 16–18):** A `_brk.mod` is a sectioned destruction model; pieces have individual pivots. The manual marks the initial explosion ordering as new in SFC3, so do not import that ordering rule into OP without separate evidence. Verify OP piece boundaries and pivots from files and its game behavior.
- **Textures (pages 5–6):** Color and illumination maps predate the SFC3 additions. Naming examples in this SFC3 manual use an `_i` suffix, whereas the supplied SFC II plugin readme describes adding `i` before the extension; actual referenced names and the asset folder are authoritative for individual models. Verify OP handling rather than hard-coding either convention as universal.

## Excluded SFC3-specific features

Dynamic LOD, progressive damage maps, the SFC3 primary/heavy hardpoint-number split, new explosion ordering, and SFC3 UI graphics and metadata are not OP requirements. The manual also labels specular intensity as new for SFC3; do not implement its SFC3 semantics as an OP requirement. General mesh-authoring advice is not a binary format specification.

## Research priorities

The installed FCA model provides a three-`MOD0` OP reference; see `mod0-investigation.md`. Inspect its header distances, point records, materials, illumination maps and break model against the plugin's read and write paths. Test resulting behavior against OP before claiming compatibility.
