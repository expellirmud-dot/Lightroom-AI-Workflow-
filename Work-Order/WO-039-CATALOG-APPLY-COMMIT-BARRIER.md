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
recoverable without double-applying exposure, and prevent technical Lightroom
verification failures from becoming photographic REVIEW decisions.

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

## Files

- `lightroom-plugin/AIExposureAssist.lrplugin/CatalogApplyBarrier.lua` (new)
- `lightroom-plugin/AIExposureAssist.lrplugin/ImportApplyAIResults.lua`
- `src/lr_ai_exposure/catalog_confirm.py`
- `tests/test_catalog_apply_commit_barrier.py` (new)
- `Work-Order/WO-039-CATALOG-APPLY-COMMIT-BARRIER.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

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
Windows/Python 3.12 and 3.13. The full pytest suite, integration suite, source
and test compilation, config smoke test, diff check and clean-tree artifact gate
all passed.

## Live acceptance

Using the existing `sess-1788136092` after installing/pulling the fix:

1. Run `Import / Apply AI Results` again.
2. The 21 already-applied targets must be recognized without a second delta.
3. Legacy `REVIEW=21 / converged=true` state must be repaired from failed apply
   evidence and reconfirmed.
4. Result must be `Verified Catalog applies: 21`, `PASS: 303`, `REVIEW: 0`,
   followed by `RERENDER_REQUIRED` rather than `Session Complete`.
5. `Prepare Next AI Package` must then be allowed to prepare the unsettled
   rerender/recheck pass.
