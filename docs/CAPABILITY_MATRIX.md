# Capability Matrix

Canonical capability register for Lightroom AI Exposure Assist.

## Status definitions

| Status | Meaning |
|---|---|
| `NOT_STARTED` | no authorized implementation exists |
| `PLANNED` | scope exists but implementation has not started |
| `IMPLEMENTED` | code/documentation exists; required validation is incomplete |
| `TESTED` | focused automated or bounded validation passed |
| `INTEGRATED` | cross-component workflow validation passed |
| `LIVE_VERIFIED` | representative Lightroom Classic operation with real project data passed |
| `BLOCKED` | work cannot continue safely until a stated condition is resolved |
| `DEFERRED` | explicitly postponed |
| `RETIRED` | removed from the active system |

Code existence supports at most `IMPLEMENTED`; tests support at most `TESTED`;
cross-component validation supports `INTEGRATED`; real Lightroom evidence is
required for `LIVE_VERIFIED`.

## Capability register

| ID | Capability | Status | Work Order | Evidence / truth | Next gate |
|---|---|---|---|---|---|
| CAP-001 | Project configuration foundation | TESTED | WO-001, WO-029 | historical config tests; WO-029 config smoke green | maintain |
| CAP-002 | Documentation governance | TESTED | WO-002..004, WO-029 | canonical index/governance/status reconciliation | WO-029 closeout review |
| CAP-003 | Job directory creation | INTEGRATED | WO-005, WO-029 | prepared-job lifecycle tests on Windows 3.12/3.13 | real folder Prepare |
| CAP-004 | Ordered image manifest | INTEGRATED | WO-005, WO-017, WO-029 | manifest identity plus saved-job tests | real full-folder manifest |
| CAP-005 | Lightroom photo identity retrieval | LIVE_VERIFIED | WO-007, WO-026, WO-028 | real selected-photo identity reached successful Analyze Only | active-folder enumeration live test |
| CAP-006 | Read-only Lightroom preview extraction | LIVE_VERIFIED | WO-015..018, WO-028 | real cache snapshot/extraction produced reconciled preview | real complete-folder Prepare |
| CAP-007 | External vision decision import | INTEGRATED | WO-023, WO-028, WO-029 | deterministic batch import, real one-photo import, saved-job CI | real multi-image external job |
| CAP-008 | AI decision schema validation | INTEGRATED | WO-009, WO-023, WO-029 | strict exact-set/schema/hash validation in saved-job CI | real folder decision set |
| CAP-009 | Exposure delta limiting | TESTED | WO-009, WO-029 | finite/range/zero-delta gates | real apply |
| CAP-010 | XMP backup and restore safety | INTEGRATED | WO-010, WO-025, WO-029 | transaction/rollback tests and saved-job apply integration | real folder apply |
| CAP-011 | `crs:Exposure2012` update | INTEGRATED | WO-011, WO-025, WO-029 | transactional saved-job test updates only Exposure2012 | real Lightroom sidecar apply |
| CAP-012 | Lightroom metadata read-back | TESTED | WO-026, WO-029 | static refresh gate and plug-in contracts | real APPLIED_VERIFIED refresh |
| CAP-013 | Reject/review suggestions | TESTED | WO-010.2, WO-028, WO-029 | aligned skills/schema plus real REVIEW result | multi-image review summary |
| CAP-014 | Automatic export | DEFERRED | — | explicitly outside MVP | none |
| CAP-015 | Repository read-first preflight skill | TESTED | WO-004 | focused preflight tests | maintain |
| CAP-017 | Lightroom menu command registration | INTEGRATED | WO-006, WO-026, WO-028 | Lightroom previously loaded plug-in; WO-029 two-command static contract green | reload two-command plug-in |
| CAP-018 | Preview validation | INTEGRATED | WO-008, WO-016, WO-023, WO-029 | JPEG byte/hash validation and self-contained job tests | real full-folder job |
| CAP-019 | Deterministic mock judge | TESTED | WO-009 | historical mock tests | maintain compatibility |
| CAP-020 | Subject-aware exposure judgment | TESTED | WO-010.1, WO-029 | canonical skill aligned to current schema | external AI folder review |
| CAP-021 | Scene-intent classification | TESTED | WO-010.1, WO-029 | canonical skill/reference bundle | external AI folder review |
| CAP-022 | Batch grouping and reference-frame selection | TESTED | WO-010.1, WO-029 | canonical skill/reference bundle | representative folder review |
| CAP-023 | Batch exposure consistency | TESTED | WO-010.1, WO-027, WO-029 | bounded batch tests and aligned skill | representative folder review |
| CAP-024 | Image relevance classification | TESTED | WO-010.2, WO-029 | canonical skill/example aligned to current schema | representative folder review |
| CAP-025 | Accidental and test-shot detection | TESTED | WO-010.2, WO-029 | triage rules bundled into job | representative folder review |
| CAP-026 | Visual quality safety triage | TESTED | WO-010.2, WO-029 | canonical quality skill/verdict mapping | representative folder review |
| CAP-031 | Analyze-only orchestration | LIVE_VERIFIED | WO-012, WO-022, WO-028 | real Lightroom Analyze Only completed | maintain compatibility |
| CAP-032 | Result/evidence reporting | INTEGRATED | WO-012, WO-022, WO-028, WO-029 | bridge, analysis, job-state, apply-evidence tests | real folder evidence reconciliation |
| CAP-033 | Cross-component error settlement | TESTED | WO-012, WO-028, WO-029 | bridge error-order and saved-job failure contracts | real prepared-job failure handling |
| CAP-034 | Prepare-once durable folder job | INTEGRATED | WO-029 | lifecycle, manifest, state, pointer, task/schema/skills tests green on Windows 3.12/3.13 | real Lightroom folder Prepare |
| CAP-035 | Job-scoped external AI task/schema/decisions | INTEGRATED | WO-029 | self-contained bundle and exact decision-directory tests green | real external AI folder review |
| CAP-036 | Process existing saved job without cache | INTEGRATED | WO-029 | process-job test proves no handoff/cache re-read | real saved-job process |
| CAP-037 | Apply existing saved job without cache/AI rerun | INTEGRATED | WO-029 | saved-job CLI test performs transactional XMP apply with no handoff | real Lightroom apply |
| CAP-038 | Non-analyzable preview failure isolation | INTEGRATED | WO-029 | terminal skip plus unrelated-image continuation test | real folder with unavailable preview |
| CAP-039 | Zero-delta no-mutation settlement | INTEGRATED | WO-029 | byte-identical XMP and `SKIPPED_NO_CHANGE` test | real zero-delta image |
| CAP-040 | Separate Lightroom Prepare/Apply commands | TESTED | WO-029 | static Lua/menu/command contract green | Lightroom-hosted two-command certification |
| CAP-041 | Automatic active-folder RAW enumeration | TESTED | WO-029 | static contract requires one active LrFolder, `getPhotos(false)`, RAW-only exclusions | real Lightroom folder enumeration |
| CAP-042 | Self-contained canonical visual skill bundle | INTEGRATED | WO-029 | job bundle contains all four skills/references/examples; missing source/bundle fails closed | external AI receives job folder only |

## WO-029 evidence

GitHub Actions run `30412526981` at
`451011ff08dbe540b0dc20fffc7c9b22ee6d4664` concluded success for both Windows
Python 3.12 and 3.13. Focused, full, config, integration, compile, diff, and
clean-tree steps passed. New Lightroom-hosted capabilities remain below
`LIVE_VERIFIED` until the real folder Prepare/Apply certification completes.
