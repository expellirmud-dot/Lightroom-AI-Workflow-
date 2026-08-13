# Project Status

LAST_UPDATED: 2026-07-29
PROJECT_PHASE: Prepared Current-Folder Lifecycle — Automated Certified, Live Certification Pending
CURRENT_WORK_ORDER: Work-Order/WO-029-FOLDER-JOB-LIFECYCLE.md
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-028-HOTFIX.md
BASELINE_MAIN_COMMIT: 243c405e46aa36116e377cfa8cb062ed37fdb44a
ACTIVE_BRANCH: wo-029-folder-job-lifecycle
DRAFT_PR: 1

## Project objective

Build a Windows-first Lightroom Classic exposure assistant that automatically prepares every eligible proprietary-RAW master in the current Lightroom folder once, packages the complete visual judgment contract for any external AI app, and later applies only validated `crs:Exposure2012` deltas to existing XMP sidecars from the same saved job.

## Verified baseline before WO-029

- A real Lightroom selection reached read-only preview-cache extraction, manifest identity reconciliation, external manual decision import, and a successful Analyze Only result for one real photo.
- Analyze Only produced one decision and zero XMP mutations.
- Transactional XMP backup, SHA-256 verification, atomic write, rollback, and bounded batch behavior had automated/pilot evidence.
- Controlled batch tests previously covered 5, 20, and 50 entries.

## WO-029 implemented behavior

- Lightroom requires exactly one active folder and automatically enumerates all directly contained eligible proprietary-RAW master photos; Ctrl+A is not required.
- Virtual copies, videos, non-RAW formats, missing paths, and duplicate source paths are excluded and counted.
- One read-only cache handoff creates a durable prepared job and stops before AI or XMP apply.
- Every job contains `AI_TASK.md`, `AI_SKILLS.md`, strict schema, manifest, state, previews, and a job-scoped decision directory.
- `AI_SKILLS.md` bundles the complete Markdown/JSON content of the four canonical visual skills, so an external AI needs only the job folder.
- Prepare records SHA-256 for selection, manifest, task, skills, and schema; saved process/apply verifies them before trusting decisions.
- `--process-job` and `--apply-job` reopen the same job without re-reading the preview cache or invoking AI again.
- Apply requires the matching Lightroom source folder and exact job-ID authorization.
- FOUND/analyzable decisions are reconciled separately from unavailable previews; every eligible image receives one terminal record.
- Zero-delta decisions leave XMP byte-identical.
- Canonical RAW/XMP paths, source-folder containment, backup path/hash, atomic checkpoint, post-write verification, rollback, and fatal rollback stop are enforced.
- Lightroom exposes separate **Prepare Current Folder** and **Apply Prepared Job** commands.

## Automated validation

GitHub Actions run `30413267495` passed on Windows Python 3.12 and 3.13 at branch head `4fd50d6faeb3f4b1e3ad8184961ce1ca94bfc553`:

- focused WO-029 prepared-job and immutable-artifact tests;
- full pytest suite;
- CLI config smoke;
- integration suite;
- compileall for source and tests;
- diff check;
- clean working-tree/no-runtime-artifact check.

Both Windows matrix jobs and every required step concluded `success`.

## Current capability level

- Python prepared-job lifecycle and saved-job apply: `INTEGRATED` by automated Windows CI.
- Lightroom folder enumeration and two-menu Lua workflow: `TESTED` by static contracts only.
- New WO-029 end-to-end folder workflow: not `LIVE_VERIFIED`.

## Remaining live gate

1. Reload the branch plug-in in Lightroom.
2. Open exactly one folder containing eligible proprietary RAW masters.
3. Run **Prepare Current Folder** and inspect the produced self-contained job and immutable hashes.
4. Give only the job folder to an external vision AI and create the exact decision set.
5. Run **Apply Prepared Job** with the same folder active.
6. Reconcile all per-image terminal records, XMP backup/hash/value evidence, and Lightroom metadata refresh.

WO-029 must remain ACTIVE and PR #1 must remain draft until this live gate passes. `main` remains at WO-028 commit `243c405`.

## Known limitations

- Existing XMP sidecars must already contain one unambiguous finite `crs:Exposure2012` value.
- Child folders are not included by `getPhotos(false)`; each Lightroom folder is prepared as its own job.
- DNG/JPEG/TIFF/PSD/video/virtual-copy inputs are intentionally excluded from writable targets.
- The external AI may process a large prepared folder in internal chunks, but it must return one exact complete decision set and preserve batch consistency.
- Legacy one-shot/Google provider code remains compatibility-only and is not the canonical workflow.
