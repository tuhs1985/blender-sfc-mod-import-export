# Proposal

## Why

We need a reliable understanding of MOD container boundaries before building the Blender importer and exporter. A read-only inspector makes format research repeatable and exposes malformed input early.

## What Changes

- Add a standalone inspector for the observed MDLS container and its top-level chunks.
- Report offsets, sizes and tags, preserving unknown chunks without guessing their meaning.
- Reject malformed boundaries and test with synthetic data and locally available samples.

## Capabilities

### New Capabilities

- `mod-container-inspection`: Read-only inspection and structural validation of observed MDLS containers.

### Modified Capabilities

None.

## Impact

Adds dependency-free Python tooling, tests and research documentation. No Blender integration, geometry decoding, file modification or game asset redistribution is included.
