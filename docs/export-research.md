# Standard exporter research

These observations guide the in-progress exporter; they do not establish game compatibility on their own. The original OP models used for comparison remain local.

## LOD header and ordering

The R4 exporter writes a 36-byte payload header after the `MDLS` chunk header. It writes a version-like value (`0x200`) at file offset 8, a calculated radius-like float at 12, the number of model objects at 16, a float at 20, and five more floats at 24–40. The plugin readme describes a configurable LOD tolerance and switching distances. The original FCA and KCA files have three `MOD0` chunks and a count of 3; both have `5.0` at offset 20 and `[0.0, 180.0, 350.0, 0.0, 0.0]` at offsets 24–40. FCA break has one `MOD0`, but retains the same five values. Another FCA with one `MOD0` has `[0.0, 100.0, 200.0, 300.0, 400.0]`.

These observations support, but do not by themselves prove, that offset 20 is tolerance and the following five floats are LOD distance settings. Do not infer LOD count from the number of nonzero floats. The exporter can sort mesh records by name or polygon count; preserve explicit user-selected ordering. Confirm exact meanings and game behavior with controlled exports before editing these fields.

An OP installation scan found 364 readable MOD headers, including eight standard models with four LODs. FCA uses 0, 180, 350, while other examples use 0, 1800, 5000 or four populated entries. R4 decompilation calls its dialog when more than one model object is found; its readme describes distance settings. D4v1ks' exporter initializes the five entries to 0, 100, 200, 300, 400. The Blender exporter retains imported values, initializes newly needed zero entries with that 100-unit baseline (extending the preceding distance when necessary), and allows optional editing in the export dialog. Runtime effects have not yet been independently confirmed.

On 2026-11-25, the user confirmed that the LOD distance option works and was satisfactory, then accepted the MOD Viewer LOD checkout as sufficient to close the remaining LOD checks. The user does not require further edge-case testing. Individual distance-triggered switching cases were not independently verified.

Closeout check on 2026-11-25: original installed OP FCA and KCA standard and break files all reproduced byte-for-byte through the geometry round-trip writer; the standard files each had three MOD0 chunks, the break files one each. This verifies serialization of those local files, not renderer or game behavior. The synthetic Python and Blender background suites and standard export OpenSpec validation also passed.

## Materials and points

The R4 material reader loads 28-byte base records and reads eight extra bytes when flag `0x20` is set. In observed files, flag `0x01` marks a diffuse-map reference, while `0x20` accompanies the additional illumination-map reference. The importer tests `0x02` when assigning smoothing-related mesh information. Other flag meanings and the safety of modifying combinations have not been established. The Blender exporter now writes added or removed material slots and diffuse/illumination references while retaining available opaque source fields; controlled Blender and source-model checks have passed, but these changes still need a viewer or game check.

Observed `PNTS` records contain three floats followed by a string-table offset. The Blender exporter writes current point empties, including added, removed, moved and renamed points. The user has confirmed point export in game, though not every edit case has been individually tested.

## Geometry and texture collisions

The binary writer preserves existing face and corner records for unchanged geometry. It supports experimental vertex-position and topology edits with normals recalculated using the old plugin's observed per-material/shared-vertex averaging. When vertex positions or LOD count change, it recalculates the header radius; unchanged geometry retains the original radius. Changed topology regenerates polygon records and may discard unrecognized per-polygon data. The game behavior of changed geometry and LOD transitions remains unverified. Smoothing preparation remains deferred.

### Radius and model size reference

The original R4 exporter routine at `10002f20` calculates the square root of the largest squared vertex distance from the origin and its caller writes that value in the header. D4v1ks' [modern exporter](https://github.com/D4v1ks/sfcplugin_public/blob/master/sfcexp/sfcexp.cpp) independently identifies this field as radius and follows the same broad calculation. Local OP FCA and KCA header values match their farthest vertices within float precision. The user confirms that SFC OP uses a separate model-size file to scale ships to their intended in-game sizes, such as frigate and heavy-cruiser sizes, and recalls an anti-cheat purpose. The read-only Remix asset `Assets/Models/model.siz` lists FCA as 8.47 and KCA as 8.38, matching the examined headers rounded to two decimals. The exact relationship between that file and the MOD header remains to be established; the exporter does not modify the size file. No files in the Remix project were edited.

The user explains that model-size control was added in a later SFC2-cycle patch to address a multiplayer exploit: a player could otherwise use an enlarged model whose locally calculated hardpoints were closer to an opponent, gaining a firing-range advantage that the other player would not see at the same position. The user's account also notes the need to verify that participants have matching files. This is user-provided historical and gameplay context; the exact implementation and file-verification mechanism have not been independently examined here.

D4v1ks' [format definitions](https://github.com/D4v1ks/sfcplugin_public/blob/master/sfcmod/sfcmod.h) specify five LOD transition entries, and the [author's notes](https://hotandspicyforums.com/sfc-mod-plugin-for-3ds-max-2026-t47567.html) report 65,536 vertices for SFC1/2. Five transition entries alone do not prove a particular OP runtime LOD maximum. Newly added LODs preserve existing transition fields; their switching behavior needs controlled verification.

The user chose five as the working maximum assumption for standard-model LODs until further evidence. This is not established as an OP runtime limit and does not introduce a new hard export rejection. Do not assume a maximum number of break pieces: the user notes many models have around five, but the actual limit and behavior above that count are unknown. Separate 16-bit record and vertex representation limits still apply.

An experimental Blender standard-model export operator now connects this foundation to newly imported collections carrying source metadata. It supports geometry, UV, material, texture-reference and point changes, including added or removed materials and points. Original FCA and KCA round-trip byte-for-byte in local Blender checks; edits on their multi-LOD meshes, materials, textures and points have been tested by parsing exported files. Viewer or game checks of these newer editing cases remain open.

Experimental break export combines pieces into one MOD0 and encodes each retained numeric piece ID in the upper half of each corner index word. Blender background tests checked original FCA and KCA break piece IDs, positions, UVs and material assignments. Further synthetic Blender tests exercise changing texture assignments and adding or removing point and material slots while preserving source record fields where applicable. The user reports successful interactive tests of Auto, Standard Model Only, Break Model Only and overwrites on 2026-11-25. The specific overwrite checkbox and cancellation cases and any MOD Viewer or OP check for this test were not described.

On 2026-11-25, the user reported a successful import/export after deleting about half the model, but an empty break object stopped export. The user requested a message while skipping empty pieces instead. The exporter now skips break objects with no evaluated faces, reports them, and keeps the original IDs of other pieces without requiring sequential names. Local Blender checks cleared one original FCA/KCA break piece and confirmed the remaining IDs were written with the gap intact; they did not establish whether MOD Viewer or OP accepts every possible gap. When no break piece has faces, Auto skips the break output and leaves an existing break file untouched.

The user subsequently confirmed that the updated exporter skipped and reported empty break pieces without stopping, and that the resulting models checked out in MOD Viewer. The exact piece-ID gaps exercised were not specified.

On 2026-11-25, the user reported that Auto export worked, but initially did not notice the output-mode dropdown. The user copied textures to the output folder for the test; the entire output folder is excluded from Git. After seeing the dropdown, the user preferred keeping it in the file browser with instructions in its right panel. An extra mode popup was removed. The user subsequently reported all three modes and overwrites passed their tests.

On 2026-11-15, the user reported importing a custom single-LOD FCA, exporting it from Blender, viewing it in a MOD viewer, and successfully testing it in OP. The user also confirmed a multi-LOD KCA in game. The specific edits and game behaviors exercised were not reported; these results do not establish that individual LOD transitions or all supported edits and models have been tested.

On 2026-11-22, the user reported successfully deleting faces, exporting the edited model, and reading the result. The application used to read the file and in-game behavior of that edit were not specified.

On 2026-11-24, the user reported that an unchanged original OP FCA exported to the project output folder and showed all three LODs in MOD Viewer. Export to its installed Program Files folder had frozen. A Blender background reproduction captured Python's `tempfile.NamedTemporaryFile` retrying in the protected folder; replacing that creation path with exclusive file creation that does not retry permission errors returned an actionable error promptly in the same sandboxed reproduction. On 2026-11-25, the user confirmed interactively that exporting to an inaccessible location now reports an error instead of freezing Blender.

On 2026-11-25, the user reported an in-game test confirming that exported hardpoints, damage points, diffuse maps and illumination maps worked correctly. The user clarified that this in-game confirmation supersedes a separate MOD Viewer check for the test.

MOD texture references in the checked originals use local stems. Two distinct images such as `C:\A\hull.png` and `C:\B\hull.bmp` both encode to `hull`, so the game cannot distinguish them by the stored reference. The exporter warns about such collisions and continues; it does not impose a texture-format restriction.
