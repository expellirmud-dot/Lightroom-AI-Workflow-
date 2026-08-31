# WO-039 — Catalog Apply Commit Barrier & Recovery

STATUS: CI_VALIDATED_LIVE_RECHECK_PENDING

## Trigger

Representative Lightroom Classic live testing on session `sess-1788136092`
proved that 21 absolute `Exposure2012` targets were applied by Lightroom, while
the plug-in immediately re-read `getDevelopSettings()` inside the same
`withWriteAccessDo()` callback and observed the old value. All 21 results were
recorded as `CATALOG_VERIFY_MISMATCH`, then Python converted those technical
verification failures to photographic `REVIEW` and incorrectly converged the
session (`PASS=303`, `REVIEW=21`, verified applies `0`). Manual Develop-module
inspection later showed the requested targets were actually present, including
`PTO_8178.NEF = -0.75` and `PTO_8180.NEF = -0.50`.

## Goal

Make Catalog mutation/verification transactionally safe, retryable and
recoverable without double-applying exposure, prevent technical Lightroom
verification failures from becoming photographic REVIEW decisions, and close
the current MVP live-certification gate without spawning a new remediation
Work Order for the same acceptance path.

## Required behavior

1. `applyDevelopSettings({ Exposure2012 = target })` remains the only Develop
   mutation in the canonical iterative route.
2. The write-access callback only validates the precondition and requests the
   absolute target. Verification occurs after the callback returns.
3. Post-commit verification is bounded polling, never a resident/unbounded
   listener. Timeout is a technical `CATALOG_VERIFY_TIMEOUT`.
4. Retry is idempotent: if current Catalog Exposure already equals the planned
   absolute target, mark it `APPLIED_VERIFIED` without applying a delta again.
5. Session confirmation is fail-closed and batch-atomic: every planned image
   must be `APPLIED_VERIFIED` and observed at target before session state may be
   advanced. Partial/technical failure leaves session state unchanged.
6. A pre-WO-039 session corrupted by the old behavior may be recovered only
   from its own `catalog-apply-evidence.json.failed_image_ids`; only those
   technical REVIEW states are reset before successful reconfirmation.
7. Canonical `Import / Apply AI Results` must rebuild apply results from current
   Catalog truth on each retry instead of trusting a stale result JSON.
8. Technical verification failure remains technical evidence; it must never be
   converted into photographic REVIEW merely to settle a session.

## Authorized scope

Implementation scope:

- `lightroom-plugin/AIExposureAssist.lrplugin/CatalogApplyBarrier.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/ImportApplyAIResults.lua`
- `src/lr_ai_exposure/catalog_confirm.py`
- `tests/test_catalog_apply_commit_barrier.py`

Owner-authorized closeout reconciliation scope:

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/DECISIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/XMP_SAFETY.md`
- `docs/DIAGNOSTIC_PREFLIGHT.md`
- `docs/AI_JUDGE_CONTRACT.md`
- `.agents/skills/exposure-judgment/SKILL.md`
- `.agents/skills/batch-consistency-review/SKILL.md`
- `.agents/skills/image-relevance-triage/SKILL.md`
- `.agents/skills/visual-quality-safety/SKILL.md`
- `Work-Order/ROADMAP-WO-015-TO-WO-020.md`
- `README.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- this Work Order

The reconciliation extension exists to align current authority/instruction
truth and remove superseded task pressure. It does not authorize unrelated
feature work, a new provider, or architecture redesign. The still-stale WO-031
diagnostic aggregate code is documented as non-blocking legacy debt rather than
silently changed without a dedicated executed test cycle.

## Automated traps

Tests must fail if:

- verification is moved back into the write transaction;
- polling becomes unbounded;
- retry stops rebuilding result truth;
- target-already-present idempotency is removed;
- an unverified result is allowed to reach session confirmation;
- legacy technical-failure evidence can no longer recover the affected IDs.

## CI evidence

GitHub Actions run #91 (`Lightroom AI Workflow Certification`) passed on both
Windows/Python 3.12 and 3.13 for the implementation commit. The full pytest
suite, integration suite, source/test compilation, config smoke, diff check and
clean-tree artifact gate passed.

Documentation/instruction reconciliation after that implementation does not
claim a new runtime validation row until CI actually executes on the reconciled
commit.

## Live acceptance

Using the existing `sess-1788136092` after installing/pulling the fix:

1. Run `Import / Apply AI Results` again.
2. The 21 already-applied targets must be recognized without a second delta.
3. Legacy `REVIEW=21 / converged=true` state must be repaired from failed apply
   evidence and reconfirmed.
4. Result must be `Verified Catalog applies: 21`, `PASS: 303`, `REVIEW: 0`,
   followed by `RERENDER_REQUIRED` rather than `Session Complete`.
5. `Prepare Next AI Package` must then be allowed to prepare the unsettled
   rerender/recheck pass after Lightroom produces a fresh render generation.

## Anti-loop closeout rule

A defect discovered while executing the live acceptance above belongs to
WO-039 when it is a direct defect of Catalog apply confirmation, recovery,
rerender transition, or the already-authorized acceptance path.

Do not create WO-040 merely to continue proving or repairing this same gate.
A new Work Order is justified only if evidence reveals a genuinely new
capability, architecture boundary, safety model, or owner product requirement
that WO-039 cannot safely own.

Stale/conflicting canonical instructions/documentation discovered during
closeout are fixed under this Work Order and are not a separate feature.

## Closeout

WO-039 may close only when:

- automated evidence remains green for the implementation/reconciliation state
  actually being delivered;
- the live acceptance above succeeds or a precise unresolved stop condition is
  recorded;
- canonical project documents/instructions are reconciled to current evidence;
- capability maturity does not exceed executed proof;
- the active Work Order pointer and project phase agree;
- remaining post-MVP work is placed in `docs/ROADMAP.md` rather than activated
  automatically.
