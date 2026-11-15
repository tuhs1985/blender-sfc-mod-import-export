# MOD container inspection

## Purpose

Allow researchers to inspect observed MOD container structure safely and consistently before decoding model geometry.

## ADDED Requirements

### Requirement: Inspect supported containers
The inspector SHALL report the input file size and each top-level chunk's tag, offset and payload size in order for an observed MDLS container.

#### Scenario: Valid file with unknown chunk
- **WHEN** a structurally valid MDLS file contains a chunk with an unfamiliar four-byte tag
- **THEN** the inspector reports the chunk without interpreting or rejecting its tag

### Requirement: Reject invalid boundaries
The inspector SHALL reject inputs with an invalid signature, truncated header, inconsistent container length, truncated chunk header, payload or required alignment padding.

#### Scenario: Truncated payload
- **WHEN** a chunk declares a payload extending beyond the container
- **THEN** inspection fails with a useful error and a nonzero exit status

### Requirement: Preserve source files
Inspection SHALL read input files without modifying them.

#### Scenario: Inspect a file
- **WHEN** a user inspects a MOD file
- **THEN** its contents remain unchanged
