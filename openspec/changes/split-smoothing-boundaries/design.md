# Design

Place smoothing choices in the export file browser for standard and break outputs: current export (default), direct corner normals, and split smoothing boundaries. Pass the chosen mode through the overwrite dialog without requiring a second smoothing choice.

For direct normals, read Blender's evaluated corner normals, transform them using the inverse-transpose object matrix and the MOD axis conversion, and serialize each corner's direction without splitting vertices. Correct winding under mirrored object transforms. Preserve the supplied normals when rewriting imported geometry instead of replacing them with calculated averages. Material flags remain as before; OP's behavior with these normals and flags requires user-directed validation.

For split boundaries, create a temporary BMesh and split manifold edges marked sharp or whose evaluated corner normal directions differ, then regenerate normals. Preserve UVs, materials, transforms, LOD ordering and break IDs. Leave the editable mesh unchanged and free temporary data. The default keeps existing paths and raw records. The current importer does not restore all stored MOD normal directions into Blender, so direct mode uses what Blender currently displays; the default remains available for unchanged source preservation.
