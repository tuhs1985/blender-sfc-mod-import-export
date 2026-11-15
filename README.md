# Blender SFC MOD Import/Export

This project aims to create a Blender add-on for importing and exporting Starfleet Command `.mod` models. It is at the research stage: there is no working importer or exporter yet.

## Reference material

The supplied 3ds Max R3 and R4 plugin packages contain compiled plugins and readme files, not source code. Their readmes describe the Starfleet Command Volume II workflow; compatibility with other SFC releases remains to be established. The original files remain in the supplied reference directories and are not included in this repository.

The documented workflow includes:

- Geometry split into level-of-detail objects, with configurable switching distances and tolerance.
- Separate sectioned break-up models, commonly named `*_brk.mod`.
- Diffuse textures alongside the model, with optional self-illumination maps named by adding `i` before the extension.
- Hardpoints named `Hardpoint1`, `Hardpoint2`, etc., and damage points such as `a1`, `a2`, and `b1`.
- Export options for smoothing and ordering levels of detail.

These describe user-visible behavior, not a specification of the binary format. The R3 readme contains a contradictory YES/NO instruction for standard versus break-up export; the R4 readme says YES for a standard model and NO for a break-up model.

See [reverse engineering](docs/reverse-engineering.md) for the decompilation workflow and [Remix reference evidence](docs/remix-reference.md) for prior model inspection and the locally retained Blender comparison fixture.

## Next steps

Investigate the MOD format and representative files, identify game-version differences, and establish round-trip tests before implementing the Blender add-on. Keep original game assets and third-party binaries out of the repository unless their redistribution is authorized.

Substantive changes use [OpenSpec](https://github.com/Fission-AI/OpenSpec). Project context and change artifacts live in `openspec/`; Codex workflow skills are in `.agents/skills/`.
