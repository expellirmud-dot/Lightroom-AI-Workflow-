# Project Status

LAST_UPDATED: 2026-07-28
PROJECT_PHASE: Scaffold and documentation governance complete
CURRENT_WORK_ORDER: None (all authorized Work Orders completed)
LATEST_COMPLETED_WORK_ORDER: `Work-Order/WO-006-LIGHTROOM-PLUGIN-SKELETON.md`
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
| `TESTED` | 6 | CAP-001 (configuration foundation), CAP-002 (documentation governance), CAP-003 (job directory creation), CAP-004 (ordered image manifest), CAP-016 (Lightroom plug-in loading), CAP-017 (menu command registration) |
| `NOT_STARTED` | 10 | CAP-005, CAP-006, CAP-007, CAP-008, CAP-009, CAP-010, CAP-011, CAP-012, CAP-013, CAP-018 (CAP-014 deferred) |
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

WO-006 — Lightroom plug-in skeleton (Info.lua, PluginInit.lua, RunExposureAssist.lua, static contract tests)
WO-007 — Preview export and manifest handoff (extends RunExposureAssist.lua; INTEGRATED target)
