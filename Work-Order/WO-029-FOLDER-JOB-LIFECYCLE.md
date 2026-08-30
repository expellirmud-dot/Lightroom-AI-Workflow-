# WO-029 — Canonical Prepared Folder Job Lifecycle

## Status

SUPERSEDED - MERGED AUTOMATED IMPLEMENTATION; LIVE FOLDER GATE FAILED

## Post-merge outcome

PR #1 was merged to `main` at
`68a020a313ab1e0ea6fcf7f7bc6da9f907ee713c` on 2026-08-13 despite this Work
Order's original draft-PR/live-certification closeout policy.

The owner subsequently verified that plug-in version 1.1.0 build 2 loads and
shows both WO-029 menu commands. The first real **Prepare Current Folder** run
failed before Python/cache/CLI execution with:

```text
The active Lightroom folder contains no eligible proprietary-RAW master photos.
```

WO-029 therefore did not pass its real full-folder acceptance gate. Its
implementation and automated evidence remain historical truth, but its
prepare-once/single-pass architecture is superseded as the canonical target by
the owner-approved Exposure Session design documented under WO-030.

## Owner decision

The program must prepare the complete current Lightroom folder once, allow any file-capable vision AI application to analyze the exported job folder using the project's complete visual skill rules, preserve those decisions, and later update only XMP `crs:Exposure2012` from the same saved job. The application must not require a second AI/API call or repeat preview-cache extraction during apply.

## Objective

Audit and reconcile repository documentation, plug-in behavior, CLI lifecycle, external decision import, visual skills, decision handling, and batch XMP apply around one canonical workflow:

```text
CURRENT_LIGHTROOM_FOLDER
→ PREPARE_JOB
→ EXTERNAL_AI_REVIEW
→ PROCESS_SAVED_JOB
→ APPLY_SAVED_JOB
```

## Canonical folder scope

- Require exactly one active Lightroom `LrFolder`.
- Read every photo directly in that folder with `getPhotos(false)`; child folders are not included.
- Include proprietary-RAW master photos only.
- Exclude and count virtual copies, videos, non-RAW formats, missing source paths, and duplicate source paths.
- No manual Ctrl+A photo selection is required.
- One prepared job must map to exactly one source folder.

## Required changes

- Add authoritative folder-job workflow documentation.
- Replace stale one-shot/API-first and selected-photo workflow claims.
- Make cache access truthfully read-only rather than claiming no cache access.
- Add prepared-job state, self-contained AI task, bundled visual skills, decision schema, job-scoped decisions, and latest-job pointer.
- Bundle all Markdown/JSON content from the four canonical visual skill directories into each prepared job.
- Hash and verify all immutable prepared-job inputs before saved-job processing or apply.
- Add saved-job validation and apply CLI operations.
- Make the Lightroom plug-in prepare the full eligible current folder once and apply the saved job separately.
- Require the matching Lightroom source folder during apply and refresh.
- Preserve legacy CLI modes only for compatibility.
- Make external decision-provider metadata AI-agnostic.
- Reconcile decisions only against analyzable previews.
- Give non-analyzable images terminal skip records.
- Skip zero-delta XMP rewrites.
- Use full canonical path equality and atomic apply checkpoints.
- Preserve backup, verification, rollback, and one-at-a-time mutation.
- Reconcile all canonical docs, governance, status, capabilities, validation evidence, and CI.

## Allowed files

- `AGENTS.md`
- `README.md`
- `.github/workflows/ci.yml`
- `config/settings.json`
- canonical files under `docs/`
- `.agents/skills/*` when required by the audit
- `src/lr_ai_exposure/main.py`
- `src/lr_ai_exposure/job_lifecycle.py`
- `src/lr_ai_exposure/ai_judge.py`
- `src/lr_ai_exposure/analysis_result.py`
- `src/lr_ai_exposure/providers/manual_app.py`
- `src/lr_ai_exposure/apply.py`
- `src/lr_ai_exposure/apply_transaction.py`
- `lightroom-plugin/AIExposureAssist.lrplugin/*`
- focused and compatibility tests
- `Work-Order/CURRENT_WORK_ORDER.md`
- this Work Order

## Forbidden changes

- No RAW/JPEG/DNG/TIFF/PSD/catalog mutation.
- No preview-cache writes.
- No new network API dependency.
- No AI process embedded inside Lightroom.
- No XMP property other than `crs:Exposure2012`.
- No unbounded concurrent XMP mutation.
- No commit of runtime artifacts.

## Acceptance criteria

- Prepare enumerates the complete eligible proprietary-RAW master set from one active Lightroom folder without manual photo selection.
- Prepare produces a complete durable job and stops before AI/apply.
- The job contains `AI_TASK.md`, `AI_SKILLS.md`, strict schema, previews, manifest, state, and job-scoped decision directory.
- `job-state.json` stores SHA-256 for selection, manifest, task, skills, and schema; any alteration invalidates saved processing/apply.
- External AI can be any app that receives only the prepared job folder.
- Process/apply reopen the same job without `--lrdata` or new handoff.
- Every eligible RAW master has one terminal apply-evidence record.
- Missing previews do not block safe unrelated analyzable images.
- Zero-delta decisions do not rewrite XMP.
- Apply requires the matching source folder and performs exact identity/path containment and transactional writes.
- Plug-in exposes separate Prepare Current Folder and Apply Prepared Job commands.
- Canonical docs agree with implementation.
- Focused, full, integration, compile, diff, and clean-tree gates pass on Windows Python 3.12 and 3.13 before live certification.
- A real Lightroom folder prepare → external AI decisions → saved-job apply smoke passes before closeout.

## Automated evidence

GitHub Actions run `30413267495` passed all required steps on Windows Python 3.12 and 3.13 at code/documentation head `4fd50d6faeb3f4b1e3ad8184961ce1ca94bfc553`. The current branch remains subject to the same CI workflow after evidence-only documentation commits.

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

Do not mark COMPLETED or merge to `main` until the real Lightroom prepared-folder certification is recorded. Keep the pull request in draft while live certification is pending.

Historical outcome: the merge occurred before this gate passed. The policy
text is retained for audit; it is not a current instruction to recreate or
reopen PR #1. WO-029 is superseded, not completed.
