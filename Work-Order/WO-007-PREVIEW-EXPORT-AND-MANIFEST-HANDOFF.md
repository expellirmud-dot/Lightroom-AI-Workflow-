# WO-007 — Preview Export and Manifest Handoff

STATUS: DONE

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

## Closeout Evidence

- **Implementation**: `lightroom-plugin/AIExposureAssist.lrplugin/RunExposureAssist.lua` extended with `LrExportSession` JPEG preview export into the active job preview directory and an ordered manifest handoff using the WO-005 schema. Preview naming is deterministic: `{seq:06d}__{raw_stem}.jpg`. No AI, XMP write, HTTP server, watcher, or catalog mutation.
- **Tests**: `tests/test_preview_export_handoff.py` — 6 tests. Validates `run`/`previewName`/`buildExportSettings` entries, naming schema, JPEG + specific-folder export settings, WO-005 manifest fields, and the no-AI/no-XMP/no-HTTP boundary. WO-006 contract test (`test_lightroom_plugin_contract.py`) also re-validated for skeleton regression.
- **Validation**: `pytest -q` → 47 passed (1 skip), 0 failed. `compileall -q src` → pass. `git diff --check` → pass (CRLF warning only).
- **Capability impact**: CAP-005 (selected-photo retrieval) → INTEGRATED. CAP-006 (rendered-preview export) → INTEGRATED. CAP-016/CAP-017 remain TESTED from WO-006.
- **Scope**: Only allowed files changed (RunExposureAssist.lua, test, traceability docs, CURRENT_WORK_ORDER.md, this work order).
- **Stop conditions respected**: contract tests require no Lightroom runtime; not yet pushed; WO-008 not started.
