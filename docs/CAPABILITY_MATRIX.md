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
| CAP-001 | Project configuration foundation | TESTED | WO-001 | historical config tests and check-config | WO-029 config regression |
| CAP-002 | Documentation governance | TESTED | WO-002..004 | index, read-first, closeout rules | WO-029 documentation reconciliation |
| CAP-003 | Job directory creation | TESTED | WO-005 | job tests | prepared-job lifecycle validation |
| CAP-004 | Ordered image manifest | TESTED | WO-005 | manifest order/identity tests | saved-job identity validation |
| CAP-005 | Lightroom selected-photo retrieval | LIVE_VERIFIED | WO-007, WO-026, WO-028 | real Lightroom selection reached successful Analyze Only | real folder Prepare command |
| CAP-006 | Read-only Lightroom preview extraction | LIVE_VERIFIED | WO-015..018, WO-028 | real cache snapshot/extraction produced reconciled preview | real multi-image folder Prepare |
| CAP-007 | External vision decision import | INTEGRATED | WO-023, WO-028 | deterministic batch provider tests plus one real Lightroom decision import | multi-image external AI job |
| CAP-008 | AI decision schema validation | TESTED | WO-009, WO-023 | strict Pydantic/manual provider tests | WO-029 saved-job CI |
| CAP-009 | Exposure delta limiting | TESTED | WO-009 | finite/range validation tests | WO-029 saved-job CI |
| CAP-010 | XMP backup and restore safety | TESTED | WO-010, WO-025 | transaction and rollback tests/pilot | real saved-job apply certification |
| CAP-011 | `crs:Exposure2012` update | TESTED | WO-011, WO-025 | XMP writer tests and transactional pilot | real saved-job apply certification |
| CAP-012 | Lightroom metadata read-back | TESTED | WO-026 | refresh gate/static plug-in tests | real APPLIED_VERIFIED refresh |
| CAP-013 | Reject/review suggestions | TESTED | WO-010.2, WO-028 | relevance/quality schema and real REVIEW result | multi-image review summary |
| CAP-014 | Automatic export | DEFERRED | — | explicitly outside MVP | none |
| CAP-015 | Repository read-first preflight skill | TESTED | WO-004 | focused preflight tests | maintain |
| CAP-017 | Lightroom menu command registration | INTEGRATED | WO-006, WO-026, WO-028 | Lightroom loaded and executed plug-in command | WO-029 two-command live validation |
| CAP-018 | Preview validation | TESTED | WO-008, WO-016 | JPEG/hash validation tests | folder Prepare CI |
| CAP-019 | Deterministic mock judge | TESTED | WO-009 | historical mock tests | maintain |
| CAP-020 | Subject-aware exposure judgment | TESTED | WO-010.1 | exposure judgment tests/skill | external AI folder review |
| CAP-021 | Scene-intent classification | TESTED | WO-010.1 | judgment tests/skill | external AI folder review |
| CAP-022 | Batch grouping and reference-frame selection | TESTED | WO-010.1 | consistency tests/skill | representative folder review |
| CAP-023 | Batch exposure consistency | TESTED | WO-010.1, WO-027 | consistency and bounded batch tests | representative folder review |
| CAP-024 | Image relevance classification | TESTED | WO-010.2 | triage tests/skill | representative folder review |
| CAP-025 | Accidental and test-shot detection | TESTED | WO-010.2 | triage tests/skill | representative folder review |
| CAP-026 | Visual quality safety triage | TESTED | WO-010.2 | quality tests/skill | representative folder review |
| CAP-031 | Analyze-only orchestration | INTEGRATED | WO-012, WO-022, WO-028 | canonical tests plus real Analyze Only | maintain compatibility |
| CAP-032 | Result/evidence reporting | INTEGRATED | WO-012, WO-022, WO-028 | bridge result and real analysis artifacts | saved-job evidence CI |
| CAP-033 | Cross-component error settlement | TESTED | WO-012, WO-028 | bridge error-order tests | real prepared-job failure handling |
| CAP-034 | Prepare-once durable folder job | IMPLEMENTED | WO-029 | branch implementation; validation pending | focused/full Windows CI |
| CAP-035 | Job-scoped external AI task/schema/decisions | IMPLEMENTED | WO-029 | branch implementation; validation pending | focused/full Windows CI |
| CAP-036 | Process existing saved job without cache | IMPLEMENTED | WO-029 | branch implementation; validation pending | focused/full Windows CI |
| CAP-037 | Apply existing saved job without cache/AI rerun | IMPLEMENTED | WO-029 | branch implementation; validation pending | focused/full Windows CI |
| CAP-038 | Non-FOUND preview failure isolation | IMPLEMENTED | WO-029 | branch implementation; validation pending | focused/full Windows CI |
| CAP-039 | Zero-delta no-mutation settlement | IMPLEMENTED | WO-029 | branch implementation; validation pending | focused/full Windows CI |
| CAP-040 | Separate Lightroom Prepare/Apply commands | IMPLEMENTED | WO-029 | branch implementation; static/live validation pending | static CI then Lightroom certification |

## Audit note

Historical rows that still reference `pending` commits in older documents are
not stronger than the executed evidence named in those rows. WO-029 must record
its actual validation commands and commit SHA before any new capability is
promoted above `IMPLEMENTED`.
