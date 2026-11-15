# Design

## Context

The R4 exporter writes a container header followed by chunks; its helpers fill payload lengths and align subsequent data to four bytes. Twelve local samples match a top-level chunk start at byte 44. These are observed SFC2-style layouts, not a universal specification.

## Goals / Non-Goals

**Goals:** Support repeatable inspection, informative failures, and tests independent of game assets or Blender.

**Non-Goals:** Decode geometry, assert semantic validity, infer SFC version compatibility, or write MOD files.

## Decisions

Use a Python standard-library command-line program with an independently callable parser. Python suits eventual Blender integration and avoids a runtime dependency. A Blender-first inspector was considered but makes early tests depend on Blender; an ad hoc hex viewer would not make checks repeatable.

Treat the header after the outer chunk header as 36 opaque bytes; start top-level chunks at offset 44. Interpret sizes as little-endian unsigned payload lengths and align each following chunk to four bytes. Require the declared outer payload to end at the file end. Report unknown tags as bytes via a safe escaped representation; never decode their contents. Validate boundaries before advancing, including padding, without requiring any particular chunk order or inventory.

## Risks / Trade-offs

- [Different versions may use other layouts] → Describe support as observed SFC2-style layout and fail without guessing.
- [Chunk boundaries do not prove semantic correctness] → State that successful inspection is structural only.
- [Game files cannot be committed] → Use synthetic fixtures in automated tests; run local samples separately.
