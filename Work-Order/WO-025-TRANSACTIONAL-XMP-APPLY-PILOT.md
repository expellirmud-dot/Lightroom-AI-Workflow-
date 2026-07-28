# WO-025: Transactional XMP Apply Pilot

## Status
QUEUED

## Objective
Authorize and prove one-image XMP apply as a guarded transaction with two-key authorization, automatic rollback, and post-write verification.

## Dependency
- WO-022 completed.
- WO-023 completed.
- WO-024 completed.
- Owner explicitly authorizes this Work Order before execution.

## Pilot Size
- Exactly 1 copied test photo for the first apply certification.
- Exactly 1 approved image ID.
- Non-zero bounded `delta_ev`.

## Scope
- Add transactional apply orchestration around the existing XMP writer.
- Require both config authorization and explicit CLI authorization.
- Automatically roll back any failed post-replace verification.
- Record immutable apply and rollback evidence.

## Allowed Files
- `src/lr_ai_exposure/main.py`
- `src/lr_ai_exposure/apply.py`
- `src/lr_ai_exposure/xmp.py`
- `src/lr_ai_exposure/apply_transaction.py`
- `tests/test_apply_transaction.py`
- `tests/test_authorized_apply_cli.py`
- `docs/XMP_SAFETY.md`
- `docs/VALIDATION_REGISTER.md`
- `Work-Order/WO-025-TRANSACTIONAL-XMP-APPLY-PILOT.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

## Forbidden Changes
- No RAW mutation.
- No Lightroom catalog or preview-cache mutation.
- No multi-image real apply.
- No permanent `apply_authorized=true` in default config.
- No apply to an image outside the exact allowlist and approved root.

## Authorization Contract
Both conditions are required:
1. `settings.apply_authorized == true` for the bounded run.
2. CLI receives `--authorize-apply <job_id>` matching the current job.

If either condition is absent, force ANALYZE_ONLY or fail closed.

## Transaction Flow
```text
reconcile manifest/selection/decision IDs
→ verify exact approved image ID
→ verify approved root containment
→ read and hash original XMP
→ create byte-preserving backup
→ verify backup SHA-256
→ write and validate temp XMP
→ atomic replace
→ validate target exposure and structure
→ success: APPLIED_VERIFIED
→ failure after replace: automatic rollback
→ verify restored target SHA-256
→ return FAILED_AFTER_REPLACE_ROLLED_BACK
```

## Required Result States
- `PROPOSED`
- `SKIPPED_NOT_APPROVED`
- `SKIPPED_POLICY_GATE`
- `FAILED_BEFORE_REPLACE`
- `APPLIED_VERIFIED`
- `FAILED_AFTER_REPLACE_ROLLED_BACK`
- `ROLLBACK_FAILED_FATAL`

## Requirements
1. Preserve exact ID-set reconciliation.
2. Preserve confidence, verdict, risk, EV, allowlist, and root-containment gates.
3. Capture original XMP SHA-256, backup SHA-256, final SHA-256, and rollback SHA-256 when applicable.
4. Automatically invoke rollback after any post-replace verification failure.
5. Treat rollback failure as fatal and stop the batch.
6. Write `apply-evidence.json` with no secrets or personal image bytes.
7. Keep default configuration unauthorized after the run.
8. Perform the first real write only against a copied pilot XMP.

## Acceptance Criteria
- One copied XMP is changed to the expected exposure.
- Backup bytes equal original bytes.
- Post-write value and XML parse verification pass.
- A forced post-write failure test proves automatic rollback.
- Restored target SHA-256 equals original SHA-256.
- No RAW, catalog, or preview-cache mutation occurs.

## Validation
```powershell
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_apply_transaction.py tests/test_authorized_apply_cli.py
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/
git diff --check
git status --short
```

## Required Success Markers
```text
TWO_KEY_AUTHORIZATION_VERIFIED
PILOT_SIZE_1
BACKUP_SHA256_VERIFIED
ATOMIC_REPLACE_VERIFIED
POST_WRITE_VALIDATION_PASSED
AUTOMATIC_ROLLBACK_PROVEN
ROLLBACK_SHA256_VERIFIED
RAW_MUTATION_0
CATALOG_MUTATION_0
CACHE_MUTATION_0
```

## Stop Conditions
- Lightroom is actively writing the same XMP or metadata boundary is uncertain.
- Backup identity cannot be verified.
- Approved ID/root reconciliation fails.
- Rollback cannot restore the original SHA-256.
- More than one real XMP target is selected.

## Closeout
Commit once after all gates pass. Do not expand beyond one copied XMP in this Work Order. Push only when explicitly authorized.
