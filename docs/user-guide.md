# SFC MOD add-on user guide

This guide covers the experimental Blender importer and exporter for Starfleet Command: Orion Pirates. The add-on's menu also names other SFC versions; compatibility with each version has not been established.

## 1. Install the add-on

1. Download the installable add-on ZIP from the [GitHub releases page](https://github.com/tuhs1985/blender-sfc-mod-import-export/releases). If you are building it from the project source, follow the archive command in the project README. This guide is also included in the ZIP as `io_scene_sfc_mod/USER_GUIDE.md`.
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Open the add-ons menu in the upper right and choose **Install from Disk**. Select the downloaded add-on ZIP.
4. Enable **Starfleet Command 1/2/OP/3 MOD Import/Export** if Blender does not enable it automatically.
5. Close Preferences. If an update gives an import error, close and restart Blender, then install or enable the updated archive again.

## 2. Import a ship

1. Choose **File > Import > Starfleet Command 1/2/OP/3 (.mod)**.
2. Select the standard model, for example `fca.mod`. In the right panel, leave **Import Smoothing** checked to use the model's stored normals, or uncheck it for flat faces. Click the import button.
3. To edit the destruction model too, repeat the import with `fca_brk.mod`.
4. In Blender's Outliner, expand the new collections to see the meshes and point objects. The standard file's LODs appear as separate meshes; the break file's debris appears as separate meshes.

In the import file browser's right panel, **Import Smoothing** is on by default. It applies the MOD's stored corner-normal directions to Blender shading and keeps flat-shaded material faces flat. Turn it off to import the faces flat without applying the stored normals. The original records are retained for unchanged standard exports in either case. Blender normalizes non-unit normals and substitutes its own direction for a zero normal, so its preview cannot reproduce those original numerical values exactly.

Importing the break model is optional. Import warnings may report missing or ambiguous texture files; the model can still be imported and the textures assigned in Blender.

## 3. Organize the objects

For imported models, keep the meshes in the model collections created by their respective imports. Recognized points are organized into child collections:

```text
SFC MOD: fca
    fca_1, fca_2, fca_3       standard LOD meshes
    HardPoints
        hardpoint1, hardpoint2, ...
    DamagePoints
        a1, a2, ...
SFC MOD: fca_brk
    fca_brk_1, fca_brk_2, ... break meshes
    any point groups from the break file
```

The exporter pairs these collections using their original filenames: `fca.mod` and `fca_brk.mod` belong together. Hardpoints such as `Hardpoint1` and damage points such as `a1` through `f3` are grouped separately; other named points, including pivots, remain directly in the model collection. Groups are created when matching points are present. Blender may add `.001` and similar suffixes to collection names when importing multiple models.

The exporter finds point empties directly in the model collection or in its `HardPoints` and `DamagePoints` child collections. It does not search other nested child collections. Keep meshes directly in the model collection and avoid linking export objects into additional collections. The exporter currently chooses the first eligible collection when an object belongs to several. Avoid importing multiple copies with the same original filename in one scene; they can make selection ambiguous.

For a model made in Blender, orient the ship with Blender **Z up** and its nose toward **−Y**. The add-on converts meshes and points to the original Max/SFC coordinate convention when exporting. MOD imports use the same Blender orientation. If you have a scene imported using version 0.4.0 or earlier, reimport the MOD or align its meshes and points to this convention before exporting; the old axis conversion is no longer used.

Place the standard and break meshes directly in one model collection. Put point empties directly there or in `HardPoints` and `DamagePoints` child collections. Use a common ship name, for example:

- Standard LODs: `fca_1`, `fca_2`, `fca_3`, and so on. Number 1 is the highest-detail mesh.
- Break pieces: `fca_brk_1`, `fca_brk_2`, and so on.
- Points: use appropriately named Blender Empty objects, for example `Hardpoint1` and `a1`.

Use a different number for each LOD and for each break piece; follow the numbering convention when adding or duplicating objects. An individual standard mesh without a numbered LOD name can be exported as one LOD. Imported meshes retain their original IDs, so existing imported objects can be renamed; give newly added meshes the matching numbered names. Empty break meshes are skipped and reported when other pieces are exported.

Hardpoints and damage points are optional for export. A model with no point objects can still be exported.

## 4. Edit the model and textures

Select the mesh you want in the Outliner. You can edit its geometry, UVs and material assignments in Blender. Select a point Empty to move or rename it. Keep unrelated ships and their points in separate collections.

The importer attempts to find referenced textures beside the MOD file. Assign or replace image textures in the material as needed. Diffuse and illumination images are separate textures in the same Blender material: diffuse connects to the Principled shader's **Base Color**, and illumination connects to **Emission Color**. The add-on does not enforce an image format.

The exported MOD stores local texture name references. OP looks in the model folder, so put the actual images beside the exported MOD yourself. The add-on reports textures outside the save folder; it does not copy or convert them. Use standard ASCII characters for point names and texture filenames referenced by the MOD, such as unaccented English letters, numbers and underscores; the game's encoding for other characters has not been established.

### View UVs for one material

1. Select the mesh and enter **Edit Mode** with `Tab`.
2. In the 3D Viewport, press `Alt+A` to deselect faces.
3. Open **Material Properties** and choose the material slot you want.
4. Click **Select** beneath the material slots. Its faces are selected, and their UVs appear in the UV Editor. Choose the associated image in the UV Editor if needed.

If every face's UVs still appear, check the UV Editor's **UV Sync Selection** setting; the displayed selection depends on that setting. Switch to Material Preview to see textures on the model.

## 5. Export

1. Select a mesh or point in the model collection or one of its point groups. If a collection contains multiple unrelated models, select a mesh to identify which model to export.
2. Choose **File > Export > Starfleet Command 1/2/OP/3 (.mod)**.
3. Select a writable output folder and enter a filename such as `fca.mod`. Saving to a separate folder is useful while testing.
4. In the right panel, choose **Output**:
   - **Auto** exports the available standard and break models, for example `fca.mod` and `fca_brk.mod`.
   - **Standard Model Only** exports the standard model and its LODs.
   - **Break Model Only** exports the destruction pieces.
5. In the right panel, choose **Smoothing** as described below. If the model has multiple LODs, its switching-distance fields are displayed directly; change any values you want. Leave them as shown to keep the existing or automatically initialized settings. Then click the export button.
6. If an output file already exists, the options dialog lists an overwrite checkbox for it, checked by default. Uncheck an existing file to leave it untouched. Cancel the dialog to stop that export.

In the export file browser's right panel, the **Smoothing** dropdown offers:

- **Keep Current Export** (default) retains the existing export behavior, including original normal records for unchanged imported geometry.
- **Direct Corner Normals** writes Blender's evaluated corner normal directions without splitting shared vertices. It uses Blender's current shading, including imported normals where Blender can represent them.
- **Split Smoothing Boundaries** splits export vertices at Blender's sharp or shading boundaries, then recalculates normals. The editable Blender mesh is not detached.

Check the results in MOD Viewer. The direct-normal option has automated checks, but its appearance in OP has not yet been established.

The export limit is 65,536 vertices per standard LOD or across the combined break model. Smoothing preparation can split vertices and increase the exported count. A mesh already near 65,000 vertices may exceed the limit after smoothing; one at 65,536 will exceed it if smoothing adds any vertices. Leave room below the limit when using smoothing preparation.

Imported LOD distances are retained. New models start with `0, 100, 200, 300, 400`; when an imported model needs an additional distance, an empty entry is initialized using 100-unit spacing. No texture images are copied into the destination automatically.

## 6. Check the result and messages

Open the exported MOD in MOD Viewer to inspect the result. If you need an in-game check, place the model and its textures where your game installation expects them; keep a backup of files you intend to replace.

If Blender reports export warnings, switch an editor area to **Text Editor** and select **SFC MOD Export Warnings** from its text dropdown. Blender may append a number to the name if earlier reports exist. The text lists details such as textures outside the output folder or skipped empty break pieces.

If Blender reports that it cannot write to the destination, choose a folder where you have write access. Protected game installation folders may require different permissions.
