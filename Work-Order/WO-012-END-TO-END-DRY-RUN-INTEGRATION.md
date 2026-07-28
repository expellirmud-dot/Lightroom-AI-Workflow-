# WO-012 — End-to-End Dry-Run Integration

STATUS: PLANNED

## Objective

Integrate the bounded workflow from an ordered manifest through preview validation, mock AI decisions, XMP proposals, and result reporting without modifying real XMP or calling external services.

## Read-First Level

`IMPACT`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Dry-run orchestration | NOT_STARTED | INTEGRATED |
| Result reporting | NOT_STARTED | INTEGRATED |
| Cross-component error settlement | NOT_STARTED | TESTED |

## Scope

- One-shot Python CLI orchestration for one job.
- Consume WO-005 manifest and WO-008 validated previews.
- Use WO-009 deterministic mock decisions.
- Use WO-010 read/backup logic and WO-011 dry-run proposal output only.
- Produce `ai-decisions.json`, `result.json`, and `run.log` deterministically.
- Settle partial failures with truthful per-image outcomes and aggregate counters.
- No external AI, real XMP mutation, automatic reject, export automation, or direct catalog access.

## Validation

Run a complete synthetic job with multiple success and failure cases. Verify deterministic outputs, no source mutation, no network access, and correct exit status. Run full pytest, compileall, diff check, and Git status review.

## Closeout

Update architecture, user instructions, capability matrix, validation register, and project status. Commit once, do not push, and do not begin WO-013.
