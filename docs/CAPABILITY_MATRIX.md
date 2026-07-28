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
| CAP-003 | Job directory creation | TESTED | WO-005 | pending | pytest 16 passed (test_job.py) compileall check git diff --check pass | WO-006 integration |
| CAP-004 | Ordered image manifest | TESTED | WO-005 | pending | pytest 16 passed (test_job.py) manifest seq contiguous + path-escape guard | WO-006 integration |
| CAP-005 | Lightroom selected-photo retrieval | INTEGRATED | WO-007 | pending | LrSelection via catalog:getTargetPhotos; WO-007 contract test | WO-008 judge integration |
| CAP-006 | Lightroom rendered-preview export | INTEGRATED | WO-007 | pending | LrExportSession JPEG render; WO-007 contract test | WO-008 judge integration |
| CAP-007 | Vision AI batch submission | NOT_STARTED | WO-008+ | — | — | AI judge reads previews |
| CAP-020 | Subject-aware exposure judgment | TESTED | WO-010.1 | pending | pytest | WO-011 |
| CAP-021 | Scene-intent classification | TESTED | WO-010.1 | pending | pytest | WO-011 |
| CAP-022 | Batch grouping and reference-frame selection | TESTED | WO-010.1 | pending | pytest | WO-011 |
| CAP-023 | Batch exposure consistency | TESTED | WO-010.1 | pending | pytest | WO-011 |
| CAP-017 | Menu command registration | TESTED | WO-006 | pending | PluginInit.lua binds `AI Exposure Assist` under Plug-in Extras | WO-007 integration |
| CAP-008 | AI decision schema validation | TESTED | WO-009 | pending | pytest 15 passed compileall check | WO-010 integration |
| CAP-009 | Exposure delta limiting | TESTED | WO-009 | pending | pytest clamp_ev compileall check | WO-010 integration |
| CAP-010 | XMP backup and restore safety | NOT_STARTED | WO-006+ | — | — | Backup before any write |
| CAP-011 | crs:Exposure2012 update | NOT_STARTED | WO-006+ | — | — | Controlled XMP apply |
| CAP-012 | Lightroom metadata read-back | NOT_STARTED | WO-007+ | — | — | User reads metadata into LR |
| CAP-013 | Reject suggestions | NOT_STARTED | WO-006+ | — | — | result.json reject list |
| CAP-014 | Automatic export | DEFERRED | — | — | Explicitly postponed past MVP | WO-007+ |
| CAP-015 | Repository read-first preflight skill | TESTED | WO-004 | pending | pytest 18 passed (8 new + 10 existing) compileall check git diff --check pass | WO-005 integration |
| CAP-018 | Preview validation | TESTED | WO-008 | pending | pytest 8 passed compileall check | WO-009 mock judge |
| CAP-019 | Deterministic mock judge | TESTED | WO-009 | pending | pytest 15 passed compileall check | WO-010 integration |
