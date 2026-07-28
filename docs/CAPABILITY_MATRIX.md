# Capability Matrix

Canonical capability register for the Lightroom AI Exposure project.

## Status Definitions

| Status | Meaning |
|---|---|
| `NOT_STARTED` | No authorized implementation exists |
| `PLANNED` | Scope is defined but implementation has not started |
| `IMPLEMENTED` | Code or documentation exists but required validation is incomplete |
| `TESTED` | Focused automated or bounded validation passed |
| `INTEGRATED` | Cross-component workflow validation passed |
| `LIVE_VERIFIED` | Verified with representative Lightroom Classic and real project data |
| `BLOCKED` | Work cannot safely continue until a stated condition is resolved |
| `DEFERRED` | Explicitly postponed outside the active delivery phase |
| `RETIRED` | No longer part of the active system |

Rules:

- Code existence supports at most `IMPLEMENTED`.
- Focused automated tests support at most `TESTED`.
- Successful cross-component validation supports `INTEGRATED`.
- Representative use with Lightroom Classic and real files is required
  for `LIVE_VERIFIED`.
- Worker reports alone do not change capability status.
- Planned work must never be recorded as completed work.

## Capability Register

| ID | Capability | Status | Work Order | Commit | Evidence | Next Gate |
|---|---|---|---|---|---|---|
| CAP-001 | Project configuration foundation | TESTED | WO-001 | a7228cc | pytest 10 passed compileall --check-config exit 0 git diff --check pass | WO-003 traceability complete |
| CAP-002 | Documentation governance | TESTED | WO-002 | 192a5e6 | AGENTS.md sections added INDEX.md created documentation closeout gate enforced | WO-003 traceability complete |
| CAP-003 | Job directory creation | NOT_STARTED | WO-003+ | — | — | WO-003 registers create |
| CAP-004 | Ordered image manifest | NOT_STARTED | WO-004+ | — | — | Plugin creates manifest.json |
| CAP-005 | Lightroom selected-photo retrieval | NOT_STARTED | WO-004+ | — | — | Plugin reads LrSelection |
| CAP-006 | Lightroom rendered-preview export | NOT_STARTED | WO-004+ | — | — | Plugin exports previews |
| CAP-007 | Vision AI batch submission | NOT_STARTED | WO-005+ | — | — | AI judge reads previews |
| CAP-008 | AI decision schema validation | NOT_STARTED | WO-005+ | — | — | Validate delta_ev confidence |
| CAP-009 | Exposure delta limiting | NOT_STARTED | WO-005+ | — | — | Clamp to maximum_delta_ev |
| CAP-010 | XMP backup and restore safety | NOT_STARTED | WO-006+ | — | — | Backup before any write |
| CAP-011 | crs:Exposure2012 update | NOT_STARTED | WO-006+ | — | — | Controlled XMP apply |
| CAP-012 | Lightroom metadata read-back | NOT_STARTED | WO-007+ | — | — | User reads metadata into LR |
| CAP-013 | Reject suggestions | NOT_STARTED | WO-006+ | — | — | result.json reject list |
| CAP-014 | Automatic export | DEFERRED | — | — | Explicitly postponed past MVP | WO-007+ |
