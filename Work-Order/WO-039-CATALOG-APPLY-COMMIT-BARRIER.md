# WO-039 — Catalog Apply Commit Barrier & Recovery

STATUS: COMPLETE_LIVE_VERIFIED
CLOSED: 2026-08-31

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
7. Canonical `Import / Apply AI Results` rebuilds apply results from current
   Catalog truth on each retry instead of trusting stale result JSON.
8. Technical verification failure remains technical evidence; it is never
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

The reconciliation extension aligned current authority/instruction truth and
removed superseded task pressure. It did not authorize unrelated feature work,
a new provider, or architecture redesign. The still-stale WO-031 diagnostic
aggregate code remains documented non-blocking legacy debt rather than being
silently changed without its own executed test cycle.

## Automated traps

Tests fail if:

- verification is moved back into the write transaction;
- polling becomes unbounded;
- retry stops rebuilding result truth;
- target-already-present idempotency is removed;
- an unverified result is allowed to reach session confirmation;
- legacy technical-failure evidence can no longer recover the affected IDs.

## CI evidence

- GitHub Actions run #91 passed on Windows/Python 3.12 and 3.13 for the WO-039
  implementation commit. Focused/full pytest, integration, compile, config,
  diff and clean-tree gates passed.
- GitHub Actions run #95 (`33355167400`) passed on `main` commit `3c1ae399`
  after the governance/instruction reconciliation, again exercising the full
  certification workflow on Windows/Python 3.12 and 3.13.

## Live acceptance — PASS

The Owner re-ran the affected real Lightroom session `sess-1788136092` using the
WO-039 implementation.

### Gate A — Catalog confirmation and recovery

`Import / Apply AI Results` returned:

```text
RERENDER_REQUIRED
Pass 1 was confirmed.
Verified Catalog applies: 21
PASS: 303
REVIEW: 0
```

This directly demonstrates that the 21 already-present absolute targets were
recognized idempotently, the old technical REVIEW contamination was repaired,
and session state advanced to rerender rather than false convergence. No second
exposure delta was required for those already-present targets.

### Gate B — Fresh next pass

After Lightroom rerender, `Prepare Next AI Package` returned:

```text
PACKAGE_READY
Session: sess-1788136092
Pass: 2
Next AI package saved successfully.
```

This demonstrates the real Lightroom iterative transition through corrected
Catalog confirmation, rerender freshness acceptance, immutable Pass 2 package
creation and `PACKAGE_READY` without re-applying Pass 1.

Gate A and Gate B satisfy the final known live technical gates defined in
`docs/ROADMAP.md`.

## Anti-loop closeout rule

A defect discovered while proving a current acceptance gate belongs to that
Work Order when it is a direct defect of the same capability/acceptance path.
Do not create WO-040 merely to repeat deterministic behavior or to continue the
same proof chain.

A new Work Order is justified only for a genuinely new capability, architecture
boundary, safety model, or Owner product requirement selected from the roadmap.

## Documentation closeout

Updated at final closeout:

- `Work-Order/CURRENT_WORK_ORDER.md`
- this Work Order
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/ROADMAP.md`

Reviewed and already reconciled by commit `3c1ae399`; no additional content
change required for closure:

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/DECISIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/XMP_SAFETY.md`
- `docs/DIAGNOSTIC_PREFLIGHT.md`
- `docs/AI_JUDGE_CONTRACT.md`
- the four bundled visual skill entrypoints
- `README.md`
- historical `Work-Order/ROADMAP-WO-015-TO-WO-020.md`

## Closeout result

Acceptance criteria are satisfied. Runtime implementation/instruction state is
CI-certified, the affected real Lightroom Catalog recovery is live-verified,
and a fresh next immutable package was created from the same session.

WO-039 is closed. The project phase is `TECHNICAL_MVP_COMPLETE`. AI photographic
quality/calibration, operator UX, packaging/distribution and optional provider
automation are post-MVP roadmap items and are not active Work Orders.
