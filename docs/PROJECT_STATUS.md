# Project Status

LAST_UPDATED: 2026-07-29
PROJECT_PHASE: Prepared Folder Lifecycle Remediation
CURRENT_WORK_ORDER: Work-Order/WO-029-FOLDER-JOB-LIFECYCLE.md
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-028-HOTFIX.md
BASELINE_MAIN_COMMIT: 243c405e46aa36116e377cfa8cb062ed37fdb44a
ACTIVE_BRANCH: wo-029-folder-job-lifecycle

## Project objective

Build a Windows-first Lightroom Classic exposure assistant that prepares the
complete selected folder once, allows any vision-capable AI app to write
job-scoped exposure decisions, and later applies only validated
`crs:Exposure2012` deltas to existing XMP sidecars.

## Verified baseline before WO-029

- Real Lightroom selection, preview-cache extraction, manifest handoff, and
  manual decision import completed successfully for one real photo.
- Analyze-only completed with one reconciled decision and zero XMP mutations.
- Transactional XMP backup, write verification, rollback, and bounded batch
  behavior have automated/pilot evidence.
- Controlled batch tests previously covered 5, 20, and 50 entries.

## WO-029 implementation status

The branch implements but has not yet closed validation for:

- prepare-once durable folder jobs;
- `AI_TASK.md`, decision schema, job state, and latest-job pointer;
- job-scoped external AI decision files;
- saved-job process and apply CLI operations without cache re-extraction;
- separate Lightroom Prepare and Apply menu commands;
- FOUND-only decision reconciliation;
- terminal records for missing previews and zero-delta decisions;
- exact canonical path checks and atomic apply checkpoints;
- provider-neutral metadata and documentation reconciliation.

Capability status remains at most `IMPLEMENTED` until the required branch and
pull-request validation executes successfully.

## Current risks and required gates

- WO-029 focused and full tests have not yet been recorded in the validation
  register.
- Lightroom Lua behavior has static contract coverage but still requires a real
  prepare-folder and apply-folder certification after automated tests pass.
- Existing XMP sidecars must already exist and contain one unambiguous
  `crs:Exposure2012` value.
- A source folder larger than the operationally accepted batch size should be
  prepared in bounded selections until representative larger-folder evidence
  exists.
- Historical capability rows and validation entries containing `pending`
  commit references remain historical debt and must not be treated as stronger
  evidence than their recorded commands.

## Next gate

1. Run Windows CI on the WO-029 branch through a pull request.
2. Repair all focused/full/integration failures.
3. Record actual validation evidence and commit SHA.
4. Perform one real Lightroom Prepare Selected Folder certification.
5. Use an external AI app to create decisions in that prepared job.
6. Perform one real Apply Prepared Job certification on an authorized folder.
7. Close WO-029 only after documentation, capability, and current-work truth
   are reconciled.
