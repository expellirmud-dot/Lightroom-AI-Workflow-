# WO-007 — Preview Export and Manifest Handoff

STATUS: PLANNED

## Objective

Export Lightroom-rendered JPEG previews for the current selection and hand an ordered manifest to the existing job runtime.

## Read-First Level

`IMPACT`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Selected-photo retrieval | NOT_STARTED | INTEGRATED |
| Rendered-preview export | NOT_STARTED | INTEGRATED |
| Manifest handoff | TESTED | INTEGRATED |

## Scope

- Lightroom SDK selection retrieval.
- Development-rendered JPEG export into the active job preview directory.
- Deterministic preview naming: `{seq:06d}__{raw_stem}.jpg`.
- Ordered manifest creation using the WO-005 schema.
- One-shot handoff boundary only; no AI, XMP, HTTP server, watcher, or catalog mutation.
- Tests must use fixtures or static contract validation without requiring Lightroom in CI.

## Safety

Do not access `.lrcat`, `.lrdata`, RAW contents, or preview caches directly. Lightroom SDK is the only source of selection and rendered previews.

## Validation

Run focused contract tests, full pytest, compileall, diff check, and Git status review. Record live Lightroom verification separately; automated tests alone must not claim `LIVE_VERIFIED`.

## Closeout

Commit exactly once. Do not push and do not begin WO-008.
