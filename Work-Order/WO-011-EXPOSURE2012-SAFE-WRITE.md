# WO-011 — Exposure2012 Safe Write

STATUS: PLANNED

## Objective

Implement a surgical, atomic update of only `crs:Exposure2012` in XMP sidecars.

## Read-First Level

`IMPACT`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Exposure2012 safe write | NOT_STARTED | TESTED |
| Atomic replace and rollback | NOT_STARTED | TESTED |

## Scope

- Compute `new_exposure = existing_exposure + validated_delta_ev`.
- Write Exposure2012 as a signed decimal EV value.
- Preserve all unrelated metadata, namespaces, and encoding where practical.
- Require a verified backup before source mutation.
- Write through a temporary file, validate, then atomically replace.
- In dry-run mode, never modify source XMP; emit a proposal artifact only.
- Prove failure paths leave original bytes intact.
- Do not modify EXIF exposure fields or any other develop setting.

## Validation

Use synthetic fixtures and byte-level comparisons for unrelated content. Test attribute and element forms, dry-run, malformed input, failed validation, and failed replace. Run focused tests, full pytest, compileall, diff check, and Git status review.

## Closeout

Update XMP safety and traceability documents, commit once, do not push, and do not begin WO-012.
