# Project Status

LAST_UPDATED: 2026-07-28
PROJECT_PHASE: Scaffold and documentation governance complete
CURRENT_WORK_ORDER: NONE
LATEST_COMPLETED_WORK_ORDER: `Work-Order/WO-010.2-IMAGE-RELEVANCE-AND-QUALITY-TRIAGE.md`
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
| `TESTED` | 5 | CAP-001 (configuration foundation), CAP-002 (documentation governance), CAP-003 (job directory creation), CAP-004 (ordered image manifest), CAP-015 (preflight skill) |
| `INTEGRATED` | 4 | CAP-005 (selected-photo retrieval), CAP-006 (rendered-preview export), CAP-016 (plug-in loading), CAP-017 (menu command registration) |
| `NOT_STARTED` | 8 | CAP-007, CAP-008, CAP-009, CAP-010, CAP-011, CAP-012, CAP-013, CAP-018 |
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

WO-007 — Preview export and manifest handoff (extends RunExposureAssist.lua; INTEGRATED via contract test)
WO-009 — AI Decision Contract and Mock Judge (Done)
WO-010 — XMP Read and Backup (next bounded seam)
