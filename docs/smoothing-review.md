# Smoothing review: manual, Max plugins, and original OP models

## Scope and sources

This is a read-only investigation of the supplied `ModelManual.pdf`, the R3/R4 SFC plugin readmes and decompiled native plugins, and original installed OP FCA and KCA normal and break models. The manual targets SFC III; its dynamic-LOD recommendations are not automatically OP requirements. The user reports that detaching faces along smoothing boundaries is an established practical workaround for SFC.

## What the documentation says

- The R3/R4 SFC II plugin readmes describe an export prompt, **Force smoothing over the entire mesh?** They say Yes disregards Max smoothing information and smooths connected polygons together, and describe that option as intended for planets and space backdrops.
- The SFC III manual instructs users to answer No to that prompt when exporting its ship example (page 28). It does not give a complete technical specification of the No case or prove that OP handles every smoothing group correctly.
- The manual says smoothing groups may need adjustment after Boolean operations or welding, and that duplicate polygons can cause smoothing problems (pages 11–13 and 17). Its advice to weld coincident vertices is presented in the context of SFC III dynamic LOD. It should not be imposed blindly on OP: welding also removes the separated vertex boundaries that the user says they use to control smoothing.

## What the plugin actually does

The following summarizes static reverse engineering, not original source code. R4 exporter function addresses are from `output/decompiled/sfcmodexp.dle.c.txt`; the R3 exporter has corresponding routines with the same observed structure.

1. **Face normals:** R4 `10001250` calculates and normalizes a face normal from triangle vertices and writes it to the polygon record.
2. **Default, non-forced smoothing:** R4 `10002640` sorts polygons by material index, then calls `100013a0` separately for each material run. The comparator at `10001580` compares the polygon material index. Inside each run, the smoothing routine sums the face normals for each shared vertex index, divides by the number of contributing faces, and writes that average to each matching polygon corner. The average is not normalized again in this routine.
3. **Force smoothing:** The other branch calls the same averaging routine over the entire mesh's polygon range instead of one material run at a time. Shared vertex indices still determine which corners participate.
4. **Max smoothing-group information:** The exporter checks whether a Max face's smoothing-group mask is nonzero and sets a bit associated with that face's material index. The material writer uses that accumulated bit to select a material flag. The normal-averaging routine itself does not compare the face smoothing-group masks; within a material run, it uses shared vertex indices. Consequently, different Max smoothing-group numbers on faces using the same material do not, by themselves, keep the computed corner normals separate in this code path. This is distinct from saying the exporter completely ignores whether smoothing is enabled.
5. **Import into Max:** In the R4 importer mesh-building code around `10001a2b`, the material flag `0x02` selects whether a face receives a smoothing group derived from the material index; otherwise the face smoothing mask is set to zero. The shown code does not reconstruct the original per-face smoothing-group masks. It also does not visibly assign the stored per-corner normals as explicit Max normals during that mesh construction. Further Max runtime tests would be needed to establish the exact final Max appearance.

## Check against original OP model data

For the original installed OP FCA and KCA models, I independently averaged the stored polygon face-normal vectors by **(material index, vertex index)** and compared those averages with every stored corner-normal vector:

| Model | LODs | Corners matching within 0.00001 |
| --- | ---: | ---: |
| FCA normal | 3 | 2,676 / 2,676 |
| KCA normal | 3 | 3,522 / 3,522 |
| FCA break | 1 | 1,983 / 1,983 |
| KCA break | 1 | 2,082 / 2,082 |

The largest absolute component difference across the checks was approximately `1.11e-7`. This is strong evidence that these files follow the plugin's per-material/shared-vertex averaging path. It does not prove every MOD file uses that path or establish how the OP renderer handles those stored values. Some stored averages are not unit-length, consistent with the lack of a second normalization in the plugin routine.

## Implications for our exporter

The user's detach workaround has a concrete explanation in the plugin: splitting a vertex at a hard boundary prevents the adjoining faces from contributing to the same shared-vertex average, even if they use the same material. Different materials also create separate averaging runs in the observed default path. Neither conclusion establishes that material boundaries should be changed just to control shading.

For now, preserve existing corner-normal records for unchanged geometry and continue rejecting vertex/topology changes until normals can be regenerated safely. Later, evaluate an optional, non-destructive export preparation that splits vertices at explicitly marked sharp edges and/or an artist-selected angle, then computes face and corner normals. Do not alter the artist's source mesh silently; compare controlled results against the original plugin and OP before declaring equivalence. Smoothing preparation remains deferred until the basic import/export workflow works.

## Follow-up: can we preserve hard edges without manual detaching?

The `POLY` layout stores a three-float face normal and a separate three-float normal within each corner record. That retains the **resulting normal values**, not necessarily the original Max smoothing-group assignments. Different corners can reference the same vertex index and still carry different normals. This is supported by both the record layout and the original files: in FCA LOD 1, 116 of 190 referenced vertices have more than one stored corner normal when considering all materials, while no observed `(vertex, material)` pair has differing corner normals in that LOD (comparison rounded to six decimals). These differences match the old exporter's per-material averaging, but the on-disk layout itself has room for per-corner values.

A local synthetic binary experiment wrote and decoded two triangles with the same vertex index and material but different corner-normal values; the data survived byte-for-byte. Separately, Blender 5.0.1 retained distinct custom split-normal directions on the two corners of a shared vertex in a small test. These tests demonstrate representational capacity in the file layout and Blender, **not** that the OP renderer honors arbitrary different normals for shared vertices under every material flag.

There is an important lossless-round-trip detail: some original corner-normal vectors are not unit length, and the FCA's third LOD has 24 zero-length corner normals. In a controlled Blender 5.0.1 test, a custom vector `(0, 0, 0.2)` was exposed as `(0, 0, 1)` and a zero custom vector resolved to an automatically computed normal. Therefore, importing normals as Blender custom normals alone cannot preserve every original numeric value. Retain the original raw corner records separately, and reuse them for truly unchanged geometry; decide how to encode edited normals only after testing the game.

### Candidate approach after the basic exporter works

1. Import the available normal directions into Blender as corner-level custom normals for an accurate editable preview where possible, while preserving the exact original records for unchanged round trips. Handle zero vectors explicitly instead of silently claiming they were preserved as Blender normals.
2. For an edited mesh, consider writing Blender's evaluated per-corner normal directions into the MOD corner records while recomputing face normals and handling the material smooth/flat flag. Use the inverse coordinate transform correctly, including the inverse-transpose rule for non-uniform scaling. How OP applies those normals and flags is unverified.
3. Provide an optional non-destructive compatibility preparation, operating on an export copy: split shared vertices at artist-marked sharp boundaries and/or an angle threshold, while retaining geometry, UVs, materials and piece IDs. This automates the user's established workaround without modifying the editable mesh. Do not split just because a material changes unless the chosen algorithm needs it; do not silently weld intentional splits.
4. Compare a controlled shared-vertex hard-edge fixture in OP with and without the split, plus its original plugin output, before selecting a default. Include unchanged binary round trips, non-unit and zero normals, multiple materials, and break pieces in that qualification.

Until those tests, direct custom normals are a promising possibility, and automatic splitting is a compatibility fallback—not a proven replacement for the user's method. No smoothing implementation or game test was performed in this investigation.

## Blender smoothing export follow-up

The add-on now offers opt-in export preparation based on Blender shading boundaries, as well as an angle alternative. It splits temporary geometry and recalculates normals; it does not preserve exact custom normal vectors. On 2026-11-25 the user reported that a real-model test worked nicely and that smoothing was respected. The application used for the final appearance check was not specified, so this result is not recorded as a specific game or MOD Viewer test.

On 2026-11-26, the user compared exports of the same Rommie model from our add-on and the separately reviewed SFC20Converter add-on. After aligning their orientation, the user reported that their smoothing looked almost the same in MOD Viewer. This comparison does not independently establish OP game rendering or exact preservation of custom normal vectors.

## D4v1ks' Max exporter and importer

Reviewed the public [D4v1ks Max exporter](https://github.com/D4v1ks/sfcplugin_public/blob/master/sfcexp/sfcexp.cpp), [importer](https://github.com/D4v1ks/sfcplugin_public/blob/master/sfcimp/sfcimp.cpp) and [MOD definitions](https://github.com/D4v1ks/sfcplugin_public/blob/master/sfcmod/sfcmod.h) on 2026-11-26. This is source review, not a new game test.

- The exporter first checks for specified Max normals, updating them where needed; when available, it reads the normal for each face corner. Otherwise it builds Max render normals. For each corner it checks the face's smoothing-group mask and selects a render normal whose smoothing group overlaps; when no smoothing group/render normal is available, it uses the face normal. Specified render normals take precedence where present.
- The chosen normal is transformed to export space and normalized. Each polygon corner receives its own normal alongside its vertex index, so separate smoothing results can be stored without automatically splitting shared vertices. The smoothing-group mask itself is used to select normals; this path does not write those original masks as per-face smoothing groups in the MOD.
- The exporter sets the material bit it names `kGouraud` (`0x02`) on exported materials. Our newly authored material path currently creates texture/illumination bits without setting this bit; imported material records generally retain their existing bits. This is a concrete difference to investigate, not proof that OP requires a change.
- D4v1ks' importer creates explicit per-corner Max normals from the stored MOD normals. Its source comments say these specified normals take precedence over smoothing groups; the older group reconstruction is commented out. Thus it reproduces the stored normal directions rather than reconstructing the original artist-assigned group masks.

This differs from our analysis of the original R4 exporter, which averaged face normals by shared vertex within material runs without comparing individual smoothing-group masks. Our Blender compatibility mode splits at shading boundaries and then regenerates shared-vertex normals. The user's Rommie MOD Viewer comparison found almost no visible difference between our output and a separate converter that also writes corner normals directly, but it did not compare D4v1ks' exporter or establish OP runtime behavior. Direct normal export and the material-flag difference are candidates for a controlled comparison, not grounds to change the released behavior without testing.

## D4v1ks versus SFC20Converter

Static comparison on 2026-11-26: both the D4v1ks Max exporter and SFC20Converter's Blender add-on export a separate normal for each face corner while retaining shared vertex indices. D4v1ks obtains explicit normals or selects Max render normals using face smoothing-group masks; SFC20Converter obtains Blender's evaluated corner normals, incorporating Blender's smooth/sharp/custom-normal state. Neither is evidence that the MOD retains original Max group numbers.

For importing, D4v1ks creates explicit Max corner normals from MOD normals. SFC20Converter sets Blender custom corner normals and identifies sharp boundaries, but its default import also welds coincident positions; this may affect deliberately detached geometry. D4v1ks' normal transformation uses a rotation derived from Max's object matrix and handles negative parity; SFC20Converter applies an inverse-transpose normal transform and handles negative parity. They are not identical approaches to nonuniform scale, and no runtime outcome is claimed here.

D4v1ks sets material flag `0x02` (his definition: Gouraud) on exported materials. SFC20Converter selects smooth (`0x02`) or flat (`0x04`) for textured materials based on stored material settings or whether it saw smooth faces; its generic and untextured material paths differ. OP's behavior for these choices requires separate verification.

The current local Rommie files attributed to our exporter and SFC20Converter each contain 20,807 vertices and 41,424 triangles. In each file, no `(material index, vertex index)` pair has multiple distinct stored corner normals when rounded to five decimals. The user found them nearly indistinguishable in MOD Viewer after aligning orientation. This particular pair therefore does not demonstrate a shared-vertex hard-normal boundary or a vertex-count advantage, and was not a D4v1ks export. No real D4v1ks output was available for a side-by-side check.

## Refit Constitution direct versus split exports — 2026-11-27

The user identified local `fca_sfc2v2.mod` as direct normals and `fca_sfc2v3.mod` as surface splitting. Both files have one LOD, 6,572 triangles, 29 matching point records, and 59 matching material records. All triangles matched by material, corner position and UV rounded to five decimals. Both have 3,594 distinct positions rounded to six decimals. The direct file contains 3,594 vertex records; the split file contains 5,842, an increase of 2,248 (62.5%). The direct file has 1,202 `(material, vertex index)` pairs with multiple distinct corner normals at five decimals; the split file has none. This is direct binary evidence that these exports exercise the intended alternative methods.

Comparing 19,716 matched corners by material, triangle positions and UVs, the median angle between normal directions is approximately 0.51 degrees, the 95th percentile approximately 8.9 degrees, and the maximum approximately 56.6 degrees. The direct normals have lengths approximately 1.0, while split normals range from approximately 0.667 to 1.0, consistent with normalization versus averaging. These are binary comparisons, not a judgment of visible quality. Local user models remain excluded from Git.

The user subsequently reported that the direct-normal version matched Blender perfectly in the visual comparison. The surface-split version was close, with a few areas of disagreement, and either method was considered usable. This is the user's observation for this model; it does not establish OP in-game rendering for every model.

## Import smoothing restoration — 2026-11-27

The user observed that imported models appeared flat. The importer now applies stored corner-normal directions as Blender custom normals, marks shading boundaries where adjacent smooth faces have differing stored directions, and keeps faces using the flat material flag flat. It does not weld or detach vertices. Blender normalizes non-unit values and resolves zero vectors automatically for display; the source records remain unchanged for an unchanged standard export. Synthetic tests cover smooth and flat faces, shared-vertex boundaries, a non-unit normal, a zero normal, standard and break imports, and direct-normal re-export.

Local Blender checks matched every tested non-zero smooth corner-normal direction against its source: 2,349/2,349 on stock FCA, 1,983/1,983 on FCA break, and 18,300/18,300 on each Refit Constitution direct-normal and split export. The FCA test contained 24 zero normals, for which Blender's automatic preview fallback applies. FCA and both Refit standard models remained byte-identical on unchanged export. User review in Blender is pending.

## Taldren MOD Viewer shading investigation — 2026-11-27

The supplied Taldren viewer archive contains the 2001 executable and manual, but no source. Its manual identifies Smooth Shade as the default and provides surface-normal and vertex-normal visualization. The executable and decompilation are retained locally under ignored `output/` paths. Findings below are from decompilation, not a game-rendering claim.

The MOD loader at `0x00404e30` reads each POLY face normal and each 28-byte corner record, including its individual normal. The built-in view drawing path `0x0041c000` applies lighting using the face normal when material bit `0x04` selects flat shading; when bit `0x02` selects smooth shading, it calculates lighting for each polygon corner using that corner's stored normal before submitting the polygon. If `0x04` is set, this path clears the smooth bit, including when both bits are present. The exact active rendering backend and final interpolation should be checked before treating this as a complete account of the user's viewer configuration.

For stock FCA LOD1, all 376 faces use materials that our current importer treats as smooth, with no zero corner normals. A local Blender test compared imported smooth corner-normal directions with the source records across all three FCA LODs: 2,349 nonzero normals matched; 24 zero normals occurred across the LODs. In FCA LOD1, 66 shared edges have stored face normals separated by more than 60 degrees while their two sides' corner normals match within the diagnostic threshold (dot >= 0.9999). Therefore, angle alone cannot identify the original intended sharp boundaries; these edges have geometrically steep adjacent faces but stored continuous normal directions. These counts are not an identification of the dish or impulse edges.

The viewer's per-corner lighting calculation is a plausible source of visual differences from Blender's viewport, which may shade with interpolated normals, but this has not been demonstrated as the cause of the specific reported dish and impulse differences. Different lights, materials, textures, renderer settings, view angles, or LODs also remain possible. Further work should identify those exact faces and compare viewer and Blender under controlled settings.

### FCA deflector rim

After the user supplied a close-up (with the desired edges manually marked sharp), the stock FCA LOD1's deflector was matched by its distinctive ten-triangle fan: center vertex 17 and ten rim edges. On all ten rim edges, the two neighboring triangles use the same material (index 5), and the stored corner-normal directions match at both endpoints (0 degrees at displayed precision). Stored face-normal angles across those edges range from approximately 87.28 to 100.65 degrees. Therefore, our current discontinuity-based sharp-edge detection correctly does not mark this ring from the recorded corner normals. Those source records do not by themselves distinguish the user's desired hard rim from an intentionally smooth transition. This analysis does not prove why the viewer and Blender visually differ there, or establish the correct interpretation of the impulse section.

### FCA impulse housing

The user's wider screenshot identifies the small rear-saucer housing. Its six-vertex outline (source vertices 38, 102, 94 across the top and 37, 123, 124 across the bottom) matches the close-up. On the four outer side and lower housing edges `(37,38)`, `(94,124)`, `(37,123)`, and `(123,124)`, normals agree at both endpoints (0 degrees at displayed precision), despite face-normal angles around 90.6 degrees; each adjacent face uses material index 3. Consequently, the current importer does not mark these edges sharp based on source-normal discontinuity. Conversely, the two upper boundary edges `(38,102)` and `(94,102)` have differing endpoint normals (approximately 89–117 degrees) and cross material indices 3 and 8; the existing detector should mark these sharp. The shared center line `(102,123)` is coplanar with matching corner normals, and should not be inferred as sharp solely from the picture. This locates actual source records but does not prove that the viewer rasterizer's lighting is the cause of perceived visual differences.

### Stored normal lengths and viewer lighting

Further tracing found a material distinction omitted in the earlier direction-only comparison: the viewer's built-in lighting routine `0x00419790` takes dot products using the stored corner-normal vector directly; in the traced branches it does not normalize that argument first. Blender's custom-normal display uses normalized directions. FCA normals near the impulse housing include magnitudes approximately 0.647, 0.727, and 0.769, and sampled deflector-rim normals include approximately 0.675–0.723. On the examined smooth rim/housing boundaries the raw vectors, including magnitude, agree across both sides, so magnitude is a potential contributor to brightness/appearance but is not a hidden discontinuity or recoverable smoothing-group assignment there. Viewer backend, lighting configuration and visual impact still require controlled testing. The 2,349/2,349 comparison above was direction-only and must not be interpreted as identical lighting.

### Controlled normal-length lighting calculation

A numerical diagnostic compared two original FCA triangle pairs: impulse faces 50/57 sharing edge 37–38, and dish faces 113/233 sharing edge 125–155. It used a single invented directional light aligned with the average normal of each pair, no ambient term, textures, clamping saturation, or real viewer camera/light state. For the viewer-like calculation it used the decompiled raw-normal dot product per corner and interpolated the resulting values. A normalized-normal Lambertian calculation was used as a simple comparison; it is not a capture or complete simulation of Blender's viewport.

For the impulse pair, the viewer-like mean corner-light values at the two face centers were 0.6983 and 0.7375; for the dish they were 0.6807 and 0.7132. The normalized interpolated-normal comparison gave 0.9705/0.9734 and 0.9752/0.9773 respectively, under the same test lights. These synthetic values demonstrate that discarded normal length can materially change lighting gradients. Both sides have identical raw vectors at their shared edge endpoints, so with this model their light remains continuous at the shared edge; this cannot by itself establish a true abrupt hard edge or explain the user's actual viewing configuration. No actual MOD Viewer or Blender rendered-pixel comparison was performed.

### Initial original-viewer A/B attempt

A local FCA copy with normalized nonzero corner normals was generated along with a byte-identical original copy. The normal vectors differ at 2,285 corners; vertex references, UVs, and other per-corner bytes were verified unchanged. Both copies were opened in the original Taldren viewer using the same default front view and LOD1, with the same local textures. At that small display scale no clear visual difference was established; this is inconclusive and is not a pixel comparison or a matched-lighting Blender comparison. The original installed FCA was reloaded after the attempt. More controlled camera/light matching and close-up capture remain necessary.

### Follow-up on other edge information

For the examined dish and impulse faces, material flags are `0x23`, selecting the viewer's smooth (`0x02`) rather than flat (`0x04`) branch; the face records contain an explicit face-normal vector, and the corner records contain vertex index, second 16-bit field, normal vector, UV, and final 32-bit value. On sampled dish faces 113/233 and impulse faces 50/57, the second field and final word are zero. The viewer drawing code uses face normals for visibility/culling and, for the flat branch, face lighting; its smooth branch uses corner normals for lighting. No separate smoothing-group or edge-sharp flag has been identified in these sampled records. This is limited to the inspected rendering path and fields, not proof that no renderer or unexamined flag can have another effect. The user's observation that the viewer shows a clean dish rim remains unresolved and is important visual evidence.
