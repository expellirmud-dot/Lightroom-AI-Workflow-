# Capability Matrix

Canonical capability register for Lightroom AI Exposure Assist.

LAST_RECONCILED: 2026-08-31
CURRENT_PHASE: TECHNICAL_MVP_COMPLETE

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
| CAP-002 | Documentation governance | TESTED | WO-002..004, WO-039 | canonical governance reconciled through technical MVP closeout | maintain |
| CAP-003 | Job/package directory creation | INTEGRATED | WO-005, WO-029, WO-037 | durable job/session package creation covered by integration tests | maintain |
| CAP-004 | Ordered image manifest | INTEGRATED | WO-005, WO-017, WO-029, WO-037 | identity/manifest contracts integrated into package workflow | maintain |
| CAP-005 | Lightroom photo identity retrieval | LIVE_VERIFIED | WO-007, WO-026, WO-028, WO-037 | real Lightroom identity path used in live workflows | maintain |
| CAP-006 | Read-only Lightroom preview extraction | LIVE_VERIFIED | WO-015..018, WO-028, WO-037 | real cache snapshot/extraction proven; canonical package reuses it | maintain |
| CAP-007 | External decision import | LIVE_VERIFIED | WO-023, WO-028, WO-037, WO-039 | representative 324-image live session imported decisions into real Catalog apply path | AI quality separate |
| CAP-008 | AI decision schema / exact-set validation | LIVE_VERIFIED | WO-009, WO-023, WO-037, WO-039 | live session decisions passed the validated package/apply boundary | maintain |
| CAP-009 | Exposure delta limiting / bounds | TESTED | WO-009, WO-034 | deterministic finite/range/quantization rules covered automatically | post-MVP calibration only |
| CAP-010 | Legacy XMP backup/restore safety | INTEGRATED | WO-010, WO-025, WO-029 | transactional sidecar path preserved for compatibility | no canonical iterative expansion |
| CAP-011 | Legacy `crs:Exposure2012` sidecar update | INTEGRATED | WO-011, WO-025, WO-029 | sidecar transaction integrated historically | not canonical iterative mutation |
| CAP-012 | Legacy metadata read-back | TESTED | WO-026, WO-029 | preserved compatibility behavior | not a Catalog-route prerequisite |
| CAP-013 | REVIEW non-mutation settlement | TESTED | WO-010.2, WO-028, WO-034 | REVIEW remains non-mutating; technical failures are separated from photographic REVIEW | maintain |
| CAP-014 | Automatic export | DEFERRED | — | explicitly outside MVP | post-MVP only if requested |
| CAP-015 | Repository read-first preflight skill | TESTED | WO-004, WO-033 | focused governance/preflight evidence | maintain |
| CAP-017 | Canonical Lightroom command registration | LIVE_VERIFIED | WO-006, WO-029, WO-037, WO-039 | Prepare, Import/Apply and Prepare Next surfaces exercised in real Lightroom | maintain |
| CAP-018 | Preview validation | INTEGRATED | WO-008, WO-016, WO-023, WO-038 | byte/SHA/Pillow/package checks integrated | maintain |
| CAP-019 | Deterministic mock/test judge | TESTED | WO-009, WO-036 | deterministic no-AI decision tooling supports bounded live testing | maintain |
| CAP-020 | Subject-aware exposure judgment contract | TESTED | WO-010.1, WO-038 | exposure skill/task contract aligned to current MVP | post-MVP photographer calibration |
| CAP-021 | Scene-intent exposure classification | TESTED | WO-010.1, WO-038 | task/skill contract exists for exposure context | post-MVP calibration |
| CAP-022 | Exposure grouping/reference selection | TESTED | WO-010.1, WO-032 | grouping/reference schema and guidance implemented/tested | representative AI review later |
| CAP-023 | Batch exposure consistency | TESTED | WO-010.1, WO-027, WO-038 | bounded consistency logic and contact-sheet context exist | representative AI calibration later |
| CAP-024 | Image relevance classification | DEFERRED | WO-010.2 | legacy skill preserved; current small-preview MVP forbids relevance/culling judgment | post-MVP only by explicit requirement |
| CAP-025 | Accidental/test-shot detection | DEFERRED | WO-010.2 | legacy skill preserved but outside current exposure-only task | post-MVP only by explicit requirement |
| CAP-026 | Blur/focus/visual-quality triage | DEFERRED | WO-010.2 | current small-preview MVP explicitly forbids this judgment | post-MVP only by explicit requirement |
| CAP-031 | Analyze-only orchestration | LIVE_VERIFIED | WO-012, WO-022, WO-028 | real Lightroom Analyze Only completed historically | compatibility only |
| CAP-032 | Result/evidence reporting | LIVE_VERIFIED | WO-012, WO-022, WO-029, WO-039 | real Gate A/B dialogs and session evidence reported corrected apply/rerender/package state | maintain |
| CAP-033 | Cross-component error settlement | LIVE_VERIFIED | WO-012, WO-028, WO-039 | affected legacy technical REVIEW state recovered in real Lightroom without converting technical failure into photographic REVIEW | maintain |
| CAP-034 | Legacy prepare-once durable folder job | INTEGRATED | WO-029 | legacy lifecycle retained for compatibility | no new canonical work |
| CAP-035 | Legacy job-scoped task/schema/decisions | INTEGRATED | WO-029 | preserved compatibility path | no new canonical work |
| CAP-036 | Legacy process saved job without cache | INTEGRATED | WO-029 | preserved compatibility path | no new canonical work |
| CAP-037 | Legacy apply saved job without AI rerun | INTEGRATED | WO-029 | preserved compatibility sidecar path | no new canonical work |
| CAP-038 | Non-analyzable preview failure isolation | INTEGRATED | WO-029 | deterministic failure isolation preserved | maintain |
| CAP-039 | Zero-delta no-mutation settlement | INTEGRATED | WO-029, WO-034 | no-change semantics preserved in canonical planning | maintain |
| CAP-040 | Legacy WO-029 two-command Lightroom route | LIVE_VERIFIED | WO-029 | historically loaded in Lightroom; now explicitly Legacy | preserve compatibility only |
| CAP-041 | Automatic whole-folder RAW enumeration | LIVE_VERIFIED | WO-029, WO-031, WO-032, WO-037, WO-039 | representative live session reached 324-image decision/apply stage | maintain |
| CAP-042 | Self-contained visual skill/task bundle | INTEGRATED | WO-029, WO-037, WO-038 | immutable package bundles task/skills/schema and rejects tampering | maintain |
| CAP-043 | Diagnostic-first current-folder report | INTEGRATED | WO-030, WO-031 | read-only Lua request + deterministic aggregation passed automated integration | live proof optional unless reactivated |
| CAP-044 | Exposure Session + immutable pass lineage | LIVE_VERIFIED | WO-030, WO-034..039 | real session `sess-1788136092` progressed from confirmed Pass 1 to `PACKAGE_READY` Pass 2 | maintain |
| CAP-045 | Lightroom render-generation freshness barrier | LIVE_VERIFIED | WO-030, WO-034, WO-037, WO-039 | after Gate A rerender, real `Prepare Next AI Package` accepted fresh generation and created Pass 2 | maintain |
| CAP-046 | Deterministic convergence / oscillation controller | INTEGRATED | WO-030, WO-034, WO-039 | implemented/tested; Gate A proved corrected `PASS=303 / REVIEW=0 / RERENDER_REQUIRED` transition | no separate live repetition required for MVP |
| CAP-047 | Persistent scene-group/reference schema | TESTED | WO-030, WO-032 | `scene_group_id`/reference fields implemented/tested; AI quality remains post-MVP | post-MVP representative AI evidence |
| CAP-048 | Provider-neutral immutable pass file contract | LIVE_VERIFIED | WO-030, WO-035..039 | real session/package/decision/apply and Pass 2 package crossed the filesystem boundary | maintain |
| CAP-049 | Metadata synchronization barrier for iterative route | RETIRED | WO-030, WO-034 | superseded by Catalog-authoritative iterative design; XMP Save/Read Metadata is not required | none for canonical route |
| CAP-050 | Risk-classified dirty state / delta preflight | TESTED | WO-030, WO-033 | governance tests and preflight self-test passed | maintain |
| CAP-051 | Contact-sheet package creation / integrity | LIVE_VERIFIED | WO-038, WO-039 | real Lightroom `Prepare Next AI Package` completed Pass 2 `PACKAGE_READY`; package pipeline remains integrity-gated automatically | post-MVP AI-use calibration only |
| CAP-052 | Catalog absolute-target apply + post-commit verification | LIVE_VERIFIED | WO-034, WO-039 | Gate A live: 21 existing absolute targets verified idempotently, PASS 303 / REVIEW 0, RERENDER_REQUIRED | maintain |

## Technical MVP evidence boundary

The old statement that CAP-044 through CAP-049 were merely `PLANNED` is
superseded. Session/package/convergence/render-barrier code has cross-component
automated evidence through WO-034..039, and the final live gates are now closed.

Representative live evidence proves:

1. a real 324-image whole-folder/session decision/apply path;
2. 21 absolute Catalog targets present and later verified idempotently;
3. corrected settlement at `PASS=303 / REVIEW=0 / RERENDER_REQUIRED`;
4. a fresh real Pass 2 package reaching `PACKAGE_READY` after rerender.

The technical MVP is therefore complete. Capabilities intentionally left at
`TESTED` or `INTEGRATED` are deterministic internals or post-MVP quality areas
whose maturity should not be inflated simply to make every row `LIVE_VERIFIED`.

There is no active technical Work Order. Future work must be selected from the
post-MVP roadmap by product need rather than generated from stale matrix gaps.
