# WO-010 — XMP Read and Backup

STATUS: DONE

## Objective

Safely locate, parse, and back up XMP sidecars without modifying source XMP.

## Read-First Level

`IMPACT`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| XMP Exposure2012 read | NOT_STARTED | TESTED | (Done) |
| XMP backup | NOT_STARTED | TESTED | (Done) |

## Scope

- Read only `crs:Exposure2012` from representative XMP fixtures.
- Support RDF attribute and XML element serialization where present.
- Interpret Exposure2012 as a signed decimal EV value.
- Create collision-safe byte-preserving backups before any later write stage.
- Reject missing, malformed, ambiguous, or invalid values without guessing.
- Do not change source XMP in this Work Order.
- Do not access real photographs or Lightroom catalog files.

## Validation

Use synthetic XMP fixtures covering serialization variants and failure cases. Prove source bytes remain unchanged. Run focused tests, full pytest, compileall, diff check, and Git status review.

## Closeout

Update XMP safety and traceability documents, commit once, do not push, and do not begin WO-011.
