# Project Status

LAST_UPDATED: 2026-07-29
PROJECT_PHASE: Reproducible CLI Certification Complete
CURRENT_WORK_ORDER: NONE
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-024-REPRODUCIBLE-CLI-CERTIFICATION.md
LATEST_COMMIT: 2c324d1
LAST_VERIFIED_EVIDENCE: Windows CI py312/py313 PASSED (GitHub Actions runs 30382636338 and 30384086375 on commits 17a82dd and e274c74)

## Project Objective

Build a Windows-first Lightroom Classic exposure assistant. Users select
photos in Lightroom Classic, the system renders previews, asks a vision
model to evaluate exposure consistency, writes approved exposure changes
to XMP sidecars, and returns a result report for the user to apply
manually.

## Current Capability Status

| Status | Count | Capabilities |
|---|---|---|
| `TESTED` | 20 | CAP-001..CAP-004, CAP-008..CAP-011, CAP-015, CAP-017..CAP-026, CAP-033 |
| `INTEGRATED` | 4 | CAP-005, CAP-006, CAP-031, CAP-032 |
| `NOT_STARTED` | 3 | CAP-007, CAP-012, CAP-013 |
| `DEFERRED` | 1 | CAP-014 (automatic export) |

## Known Risks

- REAL_XMP_APPLY_NOT_AUTHORIZED
- No Lightroom integration has been implemented or tested with real Lightroom Classic data.
- No Vision AI API integration has been implemented.
- No live XMP write has been validated against real Lightroom catalogs or XMP sidecars.
- No end-to-end workflow has been validated with the Lightroom plugin.
- The checked-in `config/settings.json` references example paths that are machine-specific.

## Next Recommended Bounded Seam

WO-025 preparation only
