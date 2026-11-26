# Tasks

- [x] 1.1 Implement and test break piece encoding, naming, transforms, materials and point handling.
- [x] 1.2 Implement and test the three output modes and discovery of imported and authored model collections.
- [ ] 1.3 Verify interactive cancellation leaves both files untouched. Per-file selection and changed-file protection have local automated coverage; the user reports overwrites passed.
- [ ] 1.4 Confirm which original OP FCA/KCA break examples were checked in MOD Viewer or OP. Both pass local exact geometry round trips, and the user confirmed edited break output in MOD Viewer.
- [x] 1.5 Encode current imported break-model texture assignments and added or removed points and material slots; test their exported records.
- [ ] 1.6 Explain the three output modes beside the dropdown in the save dialog; verify the presentation in Blender's interactive interface.
- [x] 1.7 Export correctly named break pieces added to an imported model even when they do not have importer-specific IDs; verify material graph handling and image references.
- [x] 1.8 Skip and report break objects with no evaluated faces without blocking other pieces; preserve remaining IDs, including gaps, and leave an entirely empty break model unwritten.
