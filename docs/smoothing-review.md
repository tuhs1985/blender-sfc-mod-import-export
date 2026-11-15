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
