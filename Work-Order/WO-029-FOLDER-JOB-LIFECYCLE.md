# WO-029 — Canonical Prepared Folder Job Lifecycle

## Status

ACTIVE

## Owner decision

The program must prepare the complete selected Lightroom folder once, allow any file-capable vision AI application to analyze the exported job folder, preserve those decisions, and later update only XMP Exposure2012 from the saved job. The application must not require a second AI API call or repeat preview-cache extraction during apply.

## Objective

Audit and reconcile repository documentation, plug-in behavior, CLI lifecycle, manual provider, decision handling, and batch XMP apply around one canonical workflow:

```text
PREPARE_JOB → EXTERNAL_AI_REVIEW → PROCESS_SAVED_JOB → APPLY_SAVED_JOB
```

## Required changes

- Add authoritative folder-job workflow documentation.
- Replace stale one-shot/API-first claims.
- Make cache access truthfully read-only rather than claiming no cache access.
- Add prepared-job state, AI task, schema, job-scoped decisions, and latest-job pointer.
- Add saved-job validation and apply CLI operations.
- Make the Lightroom plug-in prepare once and apply the saved job separately.
- Preserve legacy CLI modes only for compatibility.
- Make manual provider model metadata AI-agnostic.
- Reconcile decisions only against FOUND previews.
- Give non-FOUND images terminal skip records.
- Skip zero-delta XMP rewrites.
- Use full canonical path equality and atomic apply checkpoints.
- Preserve backup, verification, rollback, and one-at-a-time mutation.

## Allowed files

- `AGENTS.md`
- `README.md`
- `config/settings.json`
- canonical files under `docs/`
- `.agents/skills/*` only if required by audit
- `src/lr_ai_exposure/main.py`
- `src/lr_ai_exposure/job_lifecycle.py`
- `src/lr_ai_exposure/ai_judge.py`
- `src/lr_ai_exposure/analysis_result.py`
- `src/lr_ai_exposure/providers/manual_app.py`
- `src/lr_ai_exposure/apply.py`
- `src/lr_ai_exposure/apply_transaction.py`
- `lightroom-plugin/AIExposureAssist.lrplugin/*`
- focused tests
- `Work-Order/CURRENT_WORK_ORDER.md`
- this Work Order

## Forbidden changes

- No RAW/JPEG/catalog mutation.
- No preview-cache writes.
- No new network API dependency.
- No AI process embedded inside Lightroom.
- No XMP property other than `crs:Exposure2012`.
- No unbounded concurrent XMP mutation.
- No commit of runtime artifacts.

## Acceptance criteria

- Prepare produces a complete durable job and stops before AI/apply.
- External AI can be any app that follows `AI_TASK.md` and schema.
- Process/apply reopen the same job without `--lrdata` or new handoff.
- Decision files are scoped to the job.
- Every selected image has one terminal apply-evidence record.
- Missing previews do not block safe unrelated FOUND images.
- Zero-delta decisions do not rewrite XMP.
- Apply performs exact identity/path containment and transactional writes.
- Plug-in exposes separate Prepare and Apply commands.
- Canonical docs agree with implementation.
- Focused and full test suites pass before closeout.

## Validation

```powershell
uv run pytest -q tests/test_job_lifecycle.py tests/test_saved_job_cli.py tests/test_apply_saved_folder.py tests/test_lightroom_plugin.py
uv run pytest -q tests/
uv run pytest -q tests/integration/
python -m compileall -q src
python -m compileall -q tests
git diff --check
git status --short
```

## Closeout policy

Do not mark COMPLETED until executed validation is recorded. Do not merge to `main` while validation is failing or unavailable.
