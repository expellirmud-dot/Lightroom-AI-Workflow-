# WO-027: Controlled Batch Expansion

## Status
ACTIVE (STAGE C)

## Objective
Expand the verified one-image workflow to bounded batches while preserving identity, safety, rollback, failure isolation, and auditability.

## Dependency
- WO-022 completed.
- WO-023 completed.
- WO-024 completed.
- WO-025 completed.
- WO-026 completed.

## Expansion Stages
1. Stage A: 5 images.
2. Stage B: 20 images.
3. Stage C: 50 images.

Each stage must close independently before the next stage is authorized.

## Scope
- Add bounded batch execution and per-image settlement.
- Preserve exact decision/apply identity for every image.
- Isolate failures without corrupting successful or untouched items.
- Add batch-level consistency review and summary evidence.
- Keep concurrency conservative and configurable.

## Allowed Files
- batch orchestration modules.
- analysis and apply result models.
- provider scheduling and checkpoint modules.
- batch integration tests.
- `docs/ARCHITECTURE.md`
- `docs/AI_JUDGE_CONTRACT.md`
- `docs/XMP_SAFETY.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/PROJECT_STATUS.md`
- `Work-Order/WO-027-CONTROLLED-BATCH-EXPANSION.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

## Forbidden Changes
- No unbounded batch size.
- No uncontrolled concurrency.
- No batch-wide apply authorization without per-image allowlist reconciliation.
- No RAW, catalog, or preview-cache mutation.
- No continuation after fatal rollback or identity failure.

## Requirements
1. Define per-image terminal states:
   - `ANALYZED`
   - `REVIEW_REQUIRED`
   - `SKIPPED`
   - `PROPOSED`
   - `APPLIED_VERIFIED`
   - `FAILED_BEFORE_REPLACE`
   - `FAILED_AFTER_REPLACE_ROLLED_BACK`
   - `ROLLBACK_FAILED_FATAL`
2. Define batch terminal states:
   - `COMPLETED`
   - `COMPLETED_WITH_SKIPS`
   - `COMPLETED_WITH_ROLLBACKS`
   - `HALTED_FATAL`
3. Checkpoint after every image.
4. Resume without repeating settled items.
5. Enforce one active mutation at a time unless later evidence explicitly authorizes more.
6. Preserve exact manifest order in analysis artifacts.
7. Require per-image approved allowlist membership before apply.
8. Stop the batch on:
   - identity mismatch,
   - target mismatch,
   - rollback failure,
   - corrupted checkpoint,
   - unexpected mutation.
9. Continue safely after non-fatal per-image skip or pre-replace failure.
10. Produce:
    - per-image records,
    - batch summary,
    - counts by terminal state,
    - duration,
    - retry/rollback summary,
    - consistency-review summary.
11. Require Owner authorization before each expansion stage.

## Stage Gates
### Stage A — 5 Images
- Complete with zero identity errors.
- No rollback failure.
- Visual consistency accepted.

### Stage B — 20 Images
- Stage A closed.
- Checkpoint/resume proven.
- At least one injected non-fatal failure isolated correctly.

### Stage C — 50 Images
- Stage B closed.
- Runtime and evidence size remain bounded.
- No duplicate processing after resume.
- Batch summary reconciles exactly to manifest count.

## Acceptance Criteria
- Every selected image has exactly one terminal record.
- Batch counts sum exactly to manifest selected count.
- Settled items are not repeated after resume.
- A failed image cannot redirect or block unrelated XMP targets unless the failure is fatal.
- Rollback failure stops the batch immediately.
- No RAW, catalog, or preview-cache mutation occurs.

## Validation
```powershell
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/integration/
git diff --check
git status --short
```

## Required Success Markers
```text
STAGE_A_5_COMPLETED
STAGE_B_20_COMPLETED
STAGE_C_50_COMPLETED
EXACTLY_ONE_TERMINAL_RECORD_PER_IMAGE
CHECKPOINT_RESUME_VERIFIED
DUPLICATE_PROCESSING_0
IDENTITY_ERRORS_0
ROLLBACK_FAILURES_0
BATCH_COUNTS_RECONCILED
RAW_MUTATION_0
CATALOG_MUTATION_0
CACHE_MUTATION_0
```

## Stop Conditions
- Any stage starts before the prior stage closes.
- Batch counts do not reconcile exactly.
- A settled image is processed twice.
- Rollback failure occurs.
- An image maps to the wrong RAW, XMP, UUID, or decision.
- Owner authorization for the next stage is absent.

## Closeout
Close and commit each expansion stage independently. Do not automatically advance to the next stage. Push only when explicitly authorized.
