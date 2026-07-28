# WO-008 — Preview Validation

STATUS: PLANNED

## Objective

Validate exported preview files and their one-to-one mapping to ordered manifest entries before any AI submission.

## Read-First Level

`CODE`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Preview validation | NOT_STARTED | TESTED |

## Scope

- Implement preview existence, readability, extension, deterministic filename, sequence, and RAW-stem mapping checks.
- Preserve manifest order.
- Reject missing, duplicate, mismatched, escaped, or unexpected preview paths.
- Return structured per-image validation results.
- No image-quality judgment, network, Lightroom SDK changes, or XMP access.

## Validation

Use temporary synthetic files only. Run focused tests, full pytest, compileall, diff check, and Git status review.

## Closeout

Update capability and validation registers, commit once, do not push, and do not begin WO-009.
