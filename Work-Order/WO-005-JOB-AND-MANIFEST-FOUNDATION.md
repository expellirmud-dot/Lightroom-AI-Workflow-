# WO-005 — Job and Manifest Foundation

STATUS: DONE

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

## Closeout Evidence

- **Implementation**: `src/lr_ai_exposure/job.py` implements `create_job_directory`, `ManifestEntry`, `Manifest`, `write_manifest`, `read_manifest`, `validate_manifest_entries`. `src/lr_ai_exposure/models.py` re-exports the job API and retains `ImageDecision`/`JobResult`.
- **Tests**: `tests/test_job.py` — 16 tests covering job creation, deterministic UTF-8 manifest round-trip, duplicate `seq`/`image_id` rejection, contiguous `seq` enforcement, empty-field rejection, path-escape guard (relative and absolute), and malformed/missing manifest handling.
- **Validation**: `pytest -q` → 34 passed, 0 failed. `compileall -q src` → pass. `git diff --check` → pass (CRLF warning only).
- **Capability impact**: CAP-003 (job directory creation) → TESTED. CAP-004 (ordered image manifest) → TESTED.
- **Scope**: Only allowed files changed (`job.py`, `models.py`, `test_job.py`, traceability docs, CURRENT_WORK_ORDER.md, this work order).
- **Stop conditions respected**: no Lightroom SDK, AI, preview export, or XMP mutation implemented; no real photographs or XMP touched; not pushed; WO-006 not started.
