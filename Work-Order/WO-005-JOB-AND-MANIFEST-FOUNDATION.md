# WO-005 — Job and Manifest Foundation

STATUS: PLANNED

## Objective

Create the bounded job-directory and ordered manifest foundation used by later Lightroom handoff work.

## Read-First Level

`CODE`

Run the `project-read-first` skill before editing.

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Job directory creation | NOT_STARTED | TESTED |
| Ordered image manifest | NOT_STARTED | TESTED |

## Allowed Files

- `src/lr_ai_exposure/job.py`
- `src/lr_ai_exposure/models.py`
- `tests/test_job.py`
- `docs/CAPABILITY_MATRIX.md`
- `docs/PROJECT_STATUS.md`
- `docs/VALIDATION_REGISTER.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- This Work Order

## Requirements

- Create unique job folders beneath `runtime/jobs/`.
- Create required subdirectories without real photographs or XMP files.
- Define a strict ordered manifest-entry model.
- Preserve selection order through explicit `seq` values.
- Write and read UTF-8 `manifest.json` deterministically.
- Reject duplicate sequence numbers, duplicate identifiers, malformed paths, missing required fields, and path escape outside the job directory.
- Use `pathlib` for Windows paths.
- Do not implement Lightroom SDK, AI, preview export, or XMP mutation.

## Validation

```powershell
python -m pytest -q tests/test_job.py
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Closeout

Update traceability documents with actual evidence. Commit exactly once when all gates pass. Do not push and do not begin WO-006.
