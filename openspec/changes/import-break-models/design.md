# Design

## Context

The R4 importer splits break polygons when the upper half-word of corner indices changes. Three local break examples use consistent corner IDs; FCA has seven named pivots while two other examples have none. See `docs/mod0-investigation.md`.

## Goals / Non-Goals

**Goals:** Separate pieces with source material and UV data, maintaining placement and explicit pivot availability.

**Non-Goals:** Infer missing pivot locations, claim universal game compatibility, export, or change mesh smoothing.

## Decisions

Recognize break files by `_brk` suffix, preserve the upper half-word on each corner and group polygons by identifier. Validate all corners agree before building scene objects. For matching numbered pivot names use the corresponding point as the piece origin; retain source name and raw position. If no matching pivot exists, use a zero origin without warning; the user identifies pivot points as an SFC3 feature, not an OP requirement. Preserve points as empties and raw polygon records for future export. Reuse the normal importer material and texture pipeline.

## Risks / Trade-offs

- [Pivot numbering may vary] → Only map explicit unique numbered pivot names; do not require pivots for OP.
- [Other variants may use different semantics] → Reject mixed-corner IDs and validate with additional files.
