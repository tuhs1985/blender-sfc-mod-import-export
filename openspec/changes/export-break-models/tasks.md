# Tasks

- [x] 1.1 Implement and test break piece encoding, naming, transforms, materials and point handling.
- [x] 1.2 Implement and test the three output modes and discovery of imported and authored model collections.
- [x] 1.3 Verify interactive cancellation leaves both files untouched. The user verified Cancel; automated Blender checks also confirm unchecking both files writes nothing, per-file selection works, and changed destinations are protected.
- [x] 1.4 Close break-model checkout using the user's confirmation that edited break output worked in MOD Viewer. Original OP FCA/KCA examples pass local exact geometry round trips; which original examples were viewed was not recorded.
- [x] 1.5 Encode current imported break-model texture assignments and added or removed points and material slots; test their exported records.
- [x] 1.6 Explain the three output modes beside the dropdown in the save dialog. The user confirmed all three export modes passed interactive tests; the exact presentation check was not separately recorded.
- [x] 1.7 Export correctly named break pieces added to an imported model even when they do not have importer-specific IDs; verify material graph handling and image references.
- [x] 1.8 Skip and report break objects with no evaluated faces without blocking other pieces; preserve remaining IDs, including gaps, and leave an entirely empty break model unwritten.
