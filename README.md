# Blender SFC MOD Import/Export

This project aims to create a Blender add-on for importing and exporting Starfleet Command: Orion Pirates `.mod` models. It is at the research stage: there is no working Blender importer or exporter yet. SFC3-specific features are outside the current scope.

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

Install the archive through Blender's add-on preferences, enable **Starfleet Command 1/2/OP/3 MOD Import**, then use **File > Import > Starfleet Command 1/2/OP/3 (.mod)**. This experimental version imports observed standard models as separate LOD meshes and `_brk` models as separate pieces, with point empties, material slots, diffuse maps and approximate illumination. It has been tested in Blender 5.0.1 with original OP FCA and other local examples; compatibility with every game version remains unverified. Break pieces use matching numbered pivots when present; when absent, origins remain at the model origin without a warning. Export is not implemented. Geometry orientation beyond the confirmed FCA, pivot semantics across other models, corner normals, smoothing and game round-trip fidelity still need verification.

Break pieces follow the manual's Max authoring convention: for `kca_brk.mod`, the objects are named `kca_brk_1`, `kca_brk_2`, etc. These names are generated for Blender; the MOD contains zero-based numeric piece IDs, which are retained as `mod_piece_id` custom properties (so `kca_brk_1` has ID 0). Original named pivot records remain separate empties. Blender adds a suffix when an object name already exists in the same file; exporters must account for that rather than relying on names alone.

Texture references are retained regardless of image format. The importer loads an exact filename or, for an extensionless name, a unique matching image in a format Blender recognizes. Missing, ambiguous, or unreadable images do not prevent model import; assign or replace them in Blender as desired. This is not a claim that OP supports every Blender image format.

The planned exporter follows the same user-directed texture policy: it must not enforce a BMP-only restriction. How to encode and preserve selected references in MOD files still requires implementation and verification.

For the installed OP reference, select `C:\Program Files (x86)\Taldren Software Inc\Starfleet Command Orion Pirates\Assets\Models\fca\fca.mod` in the import dialog.

## Exporter development

An experimental binary-writing foundation is under development; it is not yet available as a Blender export operator. It preserves source bytes for unknown fields, and has passed byte-identical unchanged binary round trips against two local FCA files. Synthetic checks also cover selected UV, material-index, point and texture-reference edits. Editing meshes in Blender, complete material editing, break export, and in-game compatibility remain unverified. Imported models now retain compressed source data in their Blender collection to support future lossless exports; models imported by earlier add-on versions do not have this metadata.

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
