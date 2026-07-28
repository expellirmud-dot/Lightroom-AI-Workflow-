# Project Status

LAST_UPDATED: 2026-07-28
PROJECT_PHASE: Scaffold and documentation governance complete
CURRENT_WORK_ORDER: None (all authorized Work Orders completed)
LATEST_COMPLETED_WORK_ORDER: `Work-Order/WO-004-PROJECT-READ-FIRST-SKILL.md`
LATEST_COMMIT: pending

## Project Objective

Build a Windows-first Lightroom Classic exposure assistant. Users select
photos in Lightroom Classic, the system renders previews, asks a vision
model to evaluate exposure consistency, writes approved exposure changes
to XMP sidecars, and returns a result report for the user to apply
manually.

## Current Capability Status

| Status | Count | Capabilities |
|---|---|---|
| `TESTED` | 3 | CAP-001 (configuration foundation), CAP-002 (documentation governance), CAP-015 (read-first preflight skill) |
| `NOT_STARTED` | 11 | CAP-003 through CAP-013 |
| `DEFERRED` | 1 | CAP-014 (automatic export) |

## Known Risks

- No Lightroom integration has been implemented or tested with real
  Lightroom Classic data.
- No Vision AI API integration has been implemented.
- No XMP write path has been validated against real Lightroom catalogs
  or XMP sidecars.
- No end-to-end workflow has been validated with the Lightroom plugin.
- The checked-in `config/settings.json` references example paths that
  are machine-specific.

## Next Recommended Bounded Seam

WO-005 — AI exposure judgment — the first implementation seam
(Lightroom preview pipeline to Vision API decision and schema
validation).
