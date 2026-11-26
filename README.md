# Blender SFC MOD Import/Export

This project develops an experimental Blender add-on for importing and exporting Starfleet Command: Orion Pirates `.mod` models. SFC3-specific features are outside the current scope.

## Inspect a MOD container

With Python installed, run:

```powershell
python tools/inspect_mod.py 'C:\path\to\model.mod'
```

The read-only tool reports top-level chunk tags, offsets, and payload sizes in the observed SFC2-style layout. It checks structural boundaries, not geometry or game compatibility. Run its synthetic tests with `python -m unittest discover -s tests -v`.

Add `--geometry` to decode observed `MOD0` records and report vertex, polygon, and material-index counts for every LOD. The Python parser also exposes stored corner indices and UVs. It does not establish coordinate orientation, winding, normal interpretation, or game compatibility.

## Experimental Blender importer

The source add-on is in `addon/io_scene_sfc_mod/`; a local installable archive can be created with:

```powershell
python -c "from pathlib import Path; from zipfile import ZipFile, ZIP_DEFLATED; p=Path('addon/io_scene_sfc_mod'); z=ZipFile('output/io_scene_sfc_mod.zip','w',ZIP_DEFLATED); [z.write(p/n, 'io_scene_sfc_mod/'+n) for n in ('__init__.py','mod_format.py')]; z.close()"
```

Install the archive through Blender's add-on preferences, enable **Starfleet Command 1/2/OP/3 MOD Import/Export**, then use **File > Import > Starfleet Command 1/2/OP/3 (.mod)**. This experimental version imports observed standard models as separate LOD meshes and `_brk` models as separate pieces, with point empties, material slots, diffuse maps and approximate illumination. It has been tested in Blender 5.0.1 with original OP FCA and other local examples; compatibility with every game version remains unverified. Break pieces use matching numbered pivots when present; when absent, origins remain at the model origin without a warning. Geometry orientation beyond the confirmed FCA, pivot semantics across other models, corner normals, smoothing and game round-trip fidelity still need verification.

Break pieces follow the manual's Max authoring convention: for `kca_brk.mod`, the objects are named `kca_brk_1`, `kca_brk_2`, etc. These names are generated for Blender; the MOD contains zero-based numeric piece IDs, which are retained as `mod_piece_id` custom properties (so `kca_brk_1` has ID 0). Original named pivot records remain separate empties. Blender adds a suffix when an object name already exists in the same file; exporters must account for that rather than relying on names alone.

Texture references are retained regardless of image format. The importer loads an exact filename or, for an extensionless name, a unique matching image in a format Blender recognizes. Missing, ambiguous, or unreadable images do not prevent model import; assign or replace them in Blender as desired. This is not a claim that OP supports every Blender image format.

The planned exporter follows the same user-directed texture policy: it must not enforce a BMP-only restriction or rename images. Original MOD examples and the old Max exporter use local filename stems without directories or extensions; for example, `thisdamntexture.bmp` is referenced as `thisdamntexture`. The Blender export workflow and game behavior for other image formats still require verification.

For the installed OP reference, select `C:\Program Files (x86)\Taldren Software Inc\Starfleet Command Orion Pirates\Assets\Models\fca\fca.mod` in the import dialog.

## Experimental standard-model exporter

The add-on includes **File > Export > Starfleet Command 1/2/OP/3 (.mod)** for supported standard models imported with this version. Select a mesh or point in the imported model collection first. It preserves the original file's undecoded records and supports changes to UVs, face material indices, existing point positions/names and existing texture image references. It validates before writing, reports textures outside the save folder, and stores the complete warning list in a Blender Text Editor document.

New Blender models can be exported experimentally: place their mesh objects and named point empties in one collection, name multiple LOD meshes with a common prefix and numeric suffix (for example `fca_1`, `fca_2`), select one mesh, and export. A mesh without that naming pattern exports as a single LOD. The evaluated meshes are triangulated; UVs, diffuse and emission images, and collection empties are encoded. The new-model path and its defaults need MOD Viewer confirmation. If a mesh belongs to several collections, the first eligible collection is used. Imported models can include added or removed named LODs, object transforms and evaluated modifiers. Changed geometry recalculates the header radius and old-plugin-style normals; unchanged geometry retains original values. Existing LOD transition distances are retained, and the behavior of newly added transition entries needs verification. Blender smoothing settings and some shader settings are not encoded. Added or removed points and material slots and changed texture assignments are encoded. The user reports successful OP tests of an exported custom single-LOD FCA and a multi-LOD KCA before these newer edits were implemented.

## Experimental break-model export

The export file browser's right panel explains the **Auto**, **Standard Model Only**, and **Break Model Only** dropdown. Auto writes the available standard and break models, using `fca.mod` and `fca_brk.mod` for the chosen base name. For newly authored pieces, use names such as `fca_brk_1` and place them in the model collection; imported break objects retain their numeric piece IDs. If outputs already exist, the overwrite dialog lists them with individual checked-by-default choices. Uncheck a file to leave it untouched; cancel to write nothing. Existing files are rechecked before replacement. Blender background runs cannot display the dialog and will not overwrite existing files through the main export operator.

After selecting a destination for a standard model, the export options dialog offers **Modify LOD distances**, unchecked by default. Check it to see and edit the switch distances; leave it unchecked to keep the existing or automatically initialized settings. Imported values are retained. New models use 0, 100, 200, 300 and 400; new empty entries on an imported model extend the preceding distance by at least 100. The game behavior of edited distances remains to be verified.

Local Blender tests cover source FCA and KCA break models and an authored sample, including their geometry, piece IDs, UVs and material assignments. Imported break export also encodes changes to texture assignments and added or removed points and material slots. The user reports that all three export modes and overwrites passed their interactive tests. MOD Viewer or OP validation of this break export remains to be recorded.

Break objects with no evaluated faces are skipped and identified in the export message; other pieces still export. The exporter retains the remaining numeric IDs, including gaps, and does not rename Blender objects. If all break pieces are empty, Auto exports any available standard model without replacing an existing break file. Behavior of non-consecutive IDs in the game or MOD Viewer is not yet verified.

## Reference material

The supplied 3ds Max R3 and R4 plugin packages contain compiled plugins and readme files, not source code. Their readmes describe the Starfleet Command Volume II workflow; compatibility with other SFC releases remains to be established. The original files remain in the supplied reference directories and are not included in this repository.

The documented workflow includes:

- Geometry split into level-of-detail objects, with configurable switching distances and tolerance.
- Separate sectioned break-up models, commonly named `*_brk.mod`.
- Diffuse textures alongside the model, with optional self-illumination maps named by adding `i` before the extension.
- Hardpoints named `Hardpoint1`, `Hardpoint2`, etc., and damage points such as `a1`, `a2`, and `b1`.
- Export options for smoothing and ordering levels of detail.

These describe user-visible behavior, not a specification of the binary format. The R3 readme contains a contradictory YES/NO instruction for standard versus break-up export; the R4 readme says YES for a standard model and NO for a break-up model.

See [model manual notes](docs/model-manual-op-notes.md) for the Orion Pirates scope and relevant modeling concepts, [reverse engineering](docs/reverse-engineering.md) for the decompilation workflow, [MOD0 investigation](docs/mod0-investigation.md) for geometry research, and [Remix reference evidence](docs/remix-reference.md) for prior model inspection and the locally retained Blender comparison fixture.

## Next steps

Investigate the MOD format and representative files, identify game-version differences, and establish round-trip tests before implementing the Blender add-on. Keep original game assets and third-party binaries out of the repository unless their redistribution is authorized.

Substantive changes use [OpenSpec](https://github.com/Fission-AI/OpenSpec). Project context and change artifacts live in `openspec/`; Codex workflow skills are in `.agents/skills/`.
