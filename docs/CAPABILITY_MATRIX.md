# Capability Matrix

Canonical capability register for Lightroom AI Exposure Assist.

LAST_RECONCILED: 2026-08-31
CURRENT_PHASE: MVP_CLOSURE_LIVE_CERTIFICATION

## Status definitions

| Status | Meaning |
|---|---|
| `NOT_STARTED` | no authorized implementation exists |
| `PLANNED` | accepted scope exists but implementation has not started |
| `IMPLEMENTED` | code/contract exists; required validation is incomplete |
| `TESTED` | focused automated or bounded validation passed |
| `INTEGRATED` | cross-component workflow validation passed |
| `LIVE_VERIFIED` | representative Lightroom Classic operation with real project data passed |
| `BLOCKED` | work cannot continue safely until a stated condition is resolved |
| `DEFERRED` | intentionally outside the current active phase |
| `RETIRED` | superseded/removed from the canonical active system |

Code existence supports at most `IMPLEMENTED`; focused tests support at most
`TESTED`; cross-component evidence supports `INTEGRATED`; representative
Lightroom evidence is required for `LIVE_VERIFIED`.

## Capability register

| ID | Capability | Status | Work Order | Current evidence / truth | Next gate |
|---|---|---|---|---|---|
| CAP-001 | Project configuration foundation | TESTED | WO-001, WO-029 | config/smoke history remains valid | maintain |
| CAP-002 | Documentation governance | TESTED | WO-002..004, WO-039 | canonical governance exists; WO-039 reconciles stale project truth | finish WO-039 closeout reconciliation |
| CAP-003 | Job/package directory creation | INTEGRATED | WO-005, WO-029, WO-037 | durable job/session package creation covered by integration tests | maintain |
| CAP-004 | Ordered image manifest | INTEGRATED | WO-005, WO-017, WO-029, WO-037 | identity/manifest contracts integrated into package workflow | maintain |
| CAP-005 | Lightroom photo identity retrieval | LIVE_VERIFIED | WO-007, WO-026, WO-028, WO-037 | real Lightroom identity path used in live workflows | maintain |
| CAP-006 | Read-only Lightroom preview extraction | LIVE_VERIFIED | WO-015..018, WO-028, WO-037 | real cache snapshot/extraction proven; canonical package reuses it | maintain |
| CAP-007 | External decision import | LIVE_VERIFIED | WO-023, WO-028, WO-037, WO-039 | representative live session reached decision/apply stage for 324 images | AI quality remains separate |
| CAP-008 | AI decision schema / exact-set validation | LIVE_VERIFIED | WO-009, WO-023, WO-037, WO-039 | live session decisions passed far enough to build/apply Catalog targets | maintain |
| CAP-009 | Exposure delta limiting / bounds | TESTED | WO-009, WO-034 | deterministic finite/range/quantization rules covered automatically | representative calibration post-MVP |
| CAP-010 | Legacy XMP backup/restore safety | INTEGRATED | WO-010, WO-025, WO-029 | transactional sidecar path preserved for compatibility | no canonical iterative expansion |
| CAP-011 | Legacy `crs:Exposure2012` sidecar update | INTEGRATED | WO-011, WO-025, WO-029 | sidecar transaction integrated historically | not canonical iterative mutation |
| CAP-012 | Legacy metadata read-back | TESTED | WO-026, WO-029 | preserved compatibility behavior | not a Catalog-route prerequisite |
| CAP-013 | REVIEW non-mutation settlement | TESTED | WO-010.2, WO-028, WO-034 | REVIEW remains non-mutating; technical failures must not be mapped into it | maintain separation |
| CAP-014 | Automatic export | DEFERRED | — | explicitly outside MVP | post-MVP only if requested |
| CAP-015 | Repository read-first preflight skill | TESTED | WO-004, WO-033 | focused governance/preflight evidence | maintain |
| CAP-017 | Canonical Lightroom command registration | LIVE_VERIFIED | WO-006, WO-029, WO-037, WO-039 | canonical Prepare/Import-Apply surfaces have been exercised in real Lightroom path | Prepare Next live proof remains |
| CAP-018 | Preview validation | INTEGRATED | WO-008, WO-016, WO-023, WO-038 | byte/SHA/Pillow/package checks integrated | maintain |
| CAP-019 | Deterministic mock/test judge | TESTED | WO-009, WO-036 | deterministic no-AI decision tooling supports bounded live testing | maintain |
| CAP-020 | Subject-aware exposure judgment contract | TESTED | WO-010.1, WO-038 | exposure skill/task contract aligned to current MVP | representative photographer calibration post-MVP |
| CAP-021 | Scene-intent exposure classification | TESTED | WO-010.1, WO-038 | task/skill contract exists for exposure context | post-MVP calibration |
| CAP-022 | Exposure grouping/reference selection | TESTED | WO-010.1, WO-032 | grouping/reference schema and guidance implemented/tested | representative AI review later |
| CAP-023 | Batch exposure consistency | TESTED | WO-010.1, WO-027, WO-038 | bounded consistency logic and contact-sheet context exist | representative AI calibration later |
| CAP-024 | Image relevance classification | DEFERRED | WO-010.2 | legacy skill preserved; current small-preview MVP explicitly forbids relevance/culling judgment | post-MVP only by explicit requirement |
| CAP-025 | Accidental/test-shot detection | DEFERRED | WO-010.2 | legacy skill preserved but outside current exposure-only task | post-MVP only by explicit requirement |
| CAP-026 | Blur/focus/visual-quality triage | DEFERRED | WO-010.2 | current small-preview MVP explicitly forbids this judgment | post-MVP only by explicit requirement |
| CAP-031 | Analyze-only orchestration | LIVE_VERIFIED | WO-012, WO-022, WO-028 | real Lightroom Analyze Only completed historically | compatibility only |
| CAP-032 | Result/evidence reporting | INTEGRATED | WO-012, WO-022, WO-029, WO-039 | bridge/session/apply evidence integrated; live WO-039 evidence exposed the verification defect correctly enough for repair | finish live recheck |
| CAP-033 | Cross-component error settlement | TESTED | WO-012, WO-028, WO-039 | technical-vs-photographic failure separation now guarded by WO-039 tests | live recheck |
| CAP-034 | Legacy prepare-once durable folder job | INTEGRATED | WO-029 | legacy lifecycle retained for compatibility | no new canonical work |
| CAP-035 | Legacy job-scoped task/schema/decisions | INTEGRATED | WO-029 | preserved compatibility path | no new canonical work |
| CAP-036 | Legacy process saved job without cache | INTEGRATED | WO-029 | preserved compatibility path | no new canonical work |
| CAP-037 | Legacy apply saved job without AI rerun | INTEGRATED | WO-029 | preserved compatibility sidecar path | no new canonical work |
| CAP-038 | Non-analyzable preview failure isolation | INTEGRATED | WO-029 | deterministic failure isolation preserved | maintain |
| CAP-039 | Zero-delta no-mutation settlement | INTEGRATED | WO-029, WO-034 | no-change semantics preserved in canonical planning | maintain |
| CAP-040 | Legacy WO-029 two-command Lightroom route | LIVE_VERIFIED | WO-029 | historically loaded in Lightroom; now explicitly Legacy | preserve compatibility only |
| CAP-041 | Automatic whole-folder RAW enumeration | LIVE_VERIFIED | WO-029, WO-031, WO-032, WO-037, WO-039 | prior zero-eligible failure was superseded; representative live session reached 324-image decision/apply stage | maintain |
| CAP-042 | Self-contained visual skill/task bundle | INTEGRATED | WO-029, WO-037, WO-038 | immutable package bundles task/skills/schema and rejects tampering | maintain |
| CAP-043 | Diagnostic-first current-folder report | INTEGRATED | WO-030, WO-031 | read-only Lua request + deterministic aggregation passed automated integration | live diagnostic proof optional unless defect recurs |
| CAP-044 | Exposure Session + immutable pass lineage | INTEGRATED | WO-030, WO-034..037 | source/tests and real Pass-1 session exist; complete later-pass live lineage not yet proven | WO-039 Gate B: Prepare Next live proof |
| CAP-045 | Lightroom render-generation freshness barrier | INTEGRATED | WO-030, WO-034, WO-037 | implemented and covered by integration tests | representative Prepare Next after corrected rerender |
| CAP-046 | Deterministic convergence / oscillation controller | INTEGRATED | WO-030, WO-034, WO-039 | implemented/tested; live session exposed technical REVIEW contamination now fixed in CI | recheck PASS 303 / REVIEW 0 and correct transition |
| CAP-047 | Persistent scene-group/reference schema | TESTED | WO-030, WO-032 | `scene_group_id`/reference fields implemented and automated tests reported; safe split behavior lacks representative live proof | post-MVP representative AI evidence unless closure requires it |
| CAP-048 | Provider-neutral immutable pass file contract | LIVE_VERIFIED | WO-030, WO-035..039 | real session/package/decision/apply path crossed the filesystem boundary | provider quality remains separate |
| CAP-049 | Metadata synchronization barrier for iterative route | RETIRED | WO-030, WO-034 | superseded by Catalog-authoritative iterative design; XMP Save/Read Metadata is not required | none for canonical route |
| CAP-050 | Risk-classified dirty state / delta preflight | TESTED | WO-030, WO-033 | governance tests and preflight self-test passed | maintain |
| CAP-051 | Contact-sheet package creation / integrity | INTEGRATED | WO-038 | ordered 4×4 sheets/index, decode, tamper rejection and cleanup passed automated integration | representative external-AI use/calibration later |
| CAP-052 | Catalog absolute-target apply + post-commit verification | INTEGRATED | WO-034, WO-039 | real Lightroom proved targets landed; WO-039 post-commit/idempotent verification passed CI run #91 | current WO-039 live recheck |

## Current evidence boundary

The old statement that CAP-044 through CAP-049 are merely `PLANNED` is
superseded. Session/package/convergence/render-barrier code exists and has
cross-component automated evidence through WO-034..039. The canonical workflow
is no longer the WO-029 single-pass route.

Representative live evidence already proves a real session reached a 324-image
decision/apply stage and that 21 requested absolute Catalog targets were present
in Lightroom. That evidence does **not** yet prove WO-039's corrected
post-commit verification or a successful fresh next-pass generation.

Therefore the current technical closure boundary is narrow:

1. re-run WO-039 Import/Apply recovery and prove the 21 targets as
   `APPLIED_VERIFIED` without a second delta;
2. prove correct `PASS=303 / REVIEW=0 / RERENDER_REQUIRED` settlement;
3. after rerender, prove `Prepare Next AI Package` admits a fresh generation.

Do not create implementation Work Orders from superseded `PLANNED/BLOCKED`
entries without first reconciling this matrix against current source and
executed evidence.
