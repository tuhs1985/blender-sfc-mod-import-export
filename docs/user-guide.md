# SFC MOD add-on user guide

This guide covers the experimental Blender importer and exporter for Starfleet Command: Orion Pirates. The add-on's menu also names other SFC versions; compatibility with each version has not been established.

## 1. Install the add-on

1. Obtain the installable `io_scene_sfc_mod.zip` archive. If you are building it from this repository, follow the archive command in the [README](../README.md).
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Open the add-ons menu in the upper right and choose **Install from Disk**. Select `io_scene_sfc_mod.zip`.
4. Enable **Starfleet Command 1/2/OP/3 MOD Import/Export** if Blender does not enable it automatically.
5. Close Preferences. If an update gives an import error, close and restart Blender, then install or enable the updated archive again.

## 2. Import a ship

1. Choose **File > Import > Starfleet Command 1/2/OP/3 (.mod)**.
2. Select the standard model, for example `fca.mod`, and import it.
3. To edit the destruction model too, repeat the import with `fca_brk.mod`.
4. In Blender's Outliner, expand the new collections to see the meshes and point objects. The standard file's LODs appear as separate meshes; the break file's debris appears as separate meshes.

Importing the break model is optional. Import warnings may report missing or ambiguous texture files; the model can still be imported and the textures assigned in Blender.

## 3. Organize the objects

For imported models, keep the objects directly in the collections created by their respective imports:

```text
SFC MOD: fca
    fca_1, fca_2, fca_3       standard LOD meshes
    hardpoints and damage points
SFC MOD: fca_brk
    fca_brk_1, fca_brk_2, ... break meshes
    any points from the break file
```

The exporter pairs these collections using their original filenames: `fca.mod` and `fca_brk.mod` belong together. Keep each export object in its original collection rather than linking it to additional collections. The exporter currently chooses the first eligible collection when an object belongs to several. Avoid importing multiple copies with the same original filename in one scene; they can make selection ambiguous. Objects placed only in a nested child collection are not picked up from its parent.

For a new model made in Blender, place the standard meshes, break meshes and their point empties directly in one collection. Use a common ship name, for example:

- Standard LODs: `fca_1`, `fca_2`, `fca_3`, and so on. Number 1 is the highest-detail mesh.
- Break pieces: `fca_brk_1`, `fca_brk_2`, and so on.
- Points: use appropriately named Blender Empty objects, for example `Hardpoint1` and `a1`.

An individual standard mesh without a numbered LOD name can be exported as one LOD. Imported meshes retain their original IDs, so existing imported objects can be renamed; give newly added meshes the matching numbered names. Empty break meshes are skipped and reported when other pieces are exported.

## 4. Edit the model and textures

Select the mesh you want in the Outliner. You can edit its geometry, UVs and material assignments in Blender. Select a point Empty to move or rename it. Keep unrelated ships and their points in separate collections.

The importer attempts to find referenced textures beside the MOD file. Assign or replace image textures in the material as needed. Diffuse and illumination images are separate textures in the same Blender material: diffuse connects to the Principled shader's **Base Color**, and illumination connects to **Emission Color**. The add-on does not enforce an image format.

The exported MOD stores local texture name references. OP looks in the model folder, so put the actual images beside the exported MOD yourself. The add-on reports textures outside the save folder; it does not copy or convert them. For now, use ASCII characters for point names and texture filenames referenced by the MOD; the game's encoding for other characters has not been established.

### View UVs for one material

1. Select the mesh and enter **Edit Mode** with `Tab`.
2. In the 3D Viewport, press `Alt+A` to deselect faces.
3. Open **Material Properties** and choose the material slot you want.
4. Click **Select** beneath the material slots. Its faces are selected, and their UVs appear in the UV Editor. Choose the associated image in the UV Editor if needed.

If every face's UVs still appear, check the UV Editor's **UV Sync Selection** setting; the displayed selection depends on that setting. Switch to Material Preview to see textures on the model.

## 5. Export

1. Select a mesh or point in an imported model collection. For a newly made model, select one of its meshes.
2. Choose **File > Export > Starfleet Command 1/2/OP/3 (.mod)**.
3. Select a writable output folder and enter a filename such as `fca.mod`. Saving to a separate folder is useful while testing.
4. In the right panel, choose **Output**:
   - **Auto** exports the available standard and break models, for example `fca.mod` and `fca_brk.mod`.
   - **Standard Model Only** exports the standard model and its LODs.
   - **Break Model Only** exports the destruction pieces.
5. Click the export button. If a standard model is included, the **MOD Export Options** dialog offers **Modify LOD distances**, unchecked by default. Leave it unchecked to keep the existing or automatically initialized settings; check it to edit the distances shown.
6. If an output file already exists, the options dialog lists an overwrite checkbox for it, checked by default. Uncheck an existing file to leave it untouched. Cancel the dialog to stop that export.

Imported LOD distances are retained. New models start with `0, 100, 200, 300, 400`; when an imported model needs an additional distance, an empty entry is initialized using 100-unit spacing. No texture images are copied into the destination automatically.

## 6. Check the result and messages

Open the exported MOD in MOD Viewer to inspect the result. If you need an in-game check, place the model and its textures where your game installation expects them; keep a backup of files you intend to replace.

If Blender reports export warnings, switch an editor area to **Text Editor** and select **SFC MOD Export Warnings** from its text dropdown. Blender may append a number to the name if earlier reports exist. The text lists details such as textures outside the output folder or skipped empty break pieces.

If Blender reports that it cannot write to the destination, choose a folder where you have write access. Protected game installation folders may require different permissions.
