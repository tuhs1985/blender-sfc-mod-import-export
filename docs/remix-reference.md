# Remix project reference evidence

These notes summarize existing research from `C:\Project\SFC-Modernize Engine`. They are reference evidence, not instructions for this project. The original project was read only.

## MOD and break models

The [normal and break-model inspection](<C:/Project/SFC-Modernize%20Engine/docs/runs/2026-10-27-codex-break-model-inspection.md>) reports that four inspected normal and break files had `MDLS` containers with bounded `STRS`, `MATS`, and `MOD0` chunks. The normal examples also contained `PNTS`. Strings include material/image stems and other labels; lack of filename extensions in `STRS` does not establish that textures are missing. This inventory alone does not decode piece boundaries or establish universal chunk requirements.

A subsequent live capture of `fca_BRK.mod` identified four independently moving pieces. Its captured primary geometry ranges are contiguous, zero-based triangle ranges:

| Piece | First triangle | Triangle count | Material groups |
| --- | ---: | ---: | ---: |
| 0 | 0 | 2923 | 27 |
| 1 | 2923 | 889 | 19 |
| 2 | 3812 | 889 | 19 |
| 3 | 4701 | 1669 | 18 |

The four packets shared 3,497 original positions and covered 6,370 triangles. These ranges describe a captured runtime representation, not yet a decoded on-disk layout; do not equate a `MOD0` chunk or LOD with one debris piece. The notes also describe cumulative polygon ends in the observed native runtime model, which should be compared with the file and exporter before drawing conclusions about disk structures.

## Captured Blender fixture

The game-derived fixture is retained locally at `samples/remix-reference/20261018-202703-fca-blender.zip`, excluded from Git. SHA-256: `eab8fcd3ea9a64e103c3d9fdfeedb2e7566a3c915eafc20172440822661f1630`. Its ZIP integrity check passed on copying. It contains an OBJ, MTL, manifest, and 56 PNG textures.

The [provenance record](<C:/Project/SFC-Modernize%20Engine/docs/runs/2026-10-18-codex-live-capture-blender-export.md>) says the fixture was exported from one fresh in-game runtime capture, not read from an installed MOD file. It contains 6,370 triangles, 19,110 independent corners and 58 material groups, preserving captured positions, normals, UVs and triangle order. Use it as a comparison for a corresponding MOD import, while accounting for potential differences between on-disk data and the runtime representation. It does not by itself prove export or full round-trip fidelity.

## UV convention

The [Blender UV comparison](<C:/Project/SFC-Modernize%20Engine/docs/runs/2026-10-18-codex-blender-remix-uv-comparison.md>) reports Blender's OBJ importer preserved all 19,110 captured corner positions and UV float32 values and material associations. A controlled comparison found different vertical texture origins between Blender and the pinned Remix renderer. The proposed `v = 1 - v` correction belonged to the Remix adapter; it is not evidence for applying that correction to this project's MOD importer or exporter. Establish MOD-to-Blender conventions using direct file analysis and visual/round-trip tests.
