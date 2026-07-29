# AGENTS.md

## Project Mission

Build a Windows-first Lightroom Classic exposure assistant whose canonical
production workflow is:

```text
select all intended photos in one Lightroom folder
→ prepare all previews once
→ external vision AI writes job-scoped decisions
→ validate the same saved job
→ explicitly apply guarded Exposure2012 changes
→ refresh Lightroom metadata
```

The application must remain independent of any single AI vendor or API. The
MVP adjusts exposure only.

## Authority Order and Required Read Set

Authority order:

1. Active Work Order
2. `AGENTS.md`
3. `docs/XMP_SAFETY.md`
4. `docs/FOLDER_JOB_WORKFLOW.md`
5. `docs/ARCHITECTURE.md`
6. `docs/AI_JUDGE_CONTRACT.md`
7. `docs/DECISIONS.md`
8. Existing tests and implementation
9. `README.md`

Before any implementation or debugging task:

1. Invoke `.agents/skills/project-read-first/SKILL.md`.
2. Read `docs/INDEX.md`.
3. Read `Work-Order/CURRENT_WORK_ORDER.md`.
4. Read the active Work Order completely.
5. Read every canonical document whose update trigger matches the task.
6. Verify repository root, Git state, Serena context, and CodeGraph context.

No active Work Order, conflicting authority, or unexpected dirty files is a
stop condition.

## Canonical Runtime Lifecycle

1. Lightroom reads the current selected-photo identities.
2. `PREPARE_JOB` snapshots the preview-cache databases read-only and extracts
   the complete selected preview set once.
3. The prepared job owns its manifest, previews, AI task, schema, decisions,
   evidence, logs, and XMP backups.
4. Any vision-capable external AI application may read the prepared job and
   write one JSON decision per FOUND preview.
5. `PROCESS_SAVED_JOB` validates the decisions without touching XMP.
6. `APPLY_SAVED_JOB` reopens the same job, derives the safe per-image allowlist,
   and performs guarded XMP transactions.
7. Lightroom refreshes metadata only for `APPLIED_VERIFIED` images.

The apply stage must not repeat cache extraction, create a replacement job, or
call an AI provider again.

## Runtime Ownership Rules

- Lightroom plug-in owns selection identity, prepare invocation, explicit
  apply invocation, and metadata refresh.
- Cache extractor owns read-only SQLite snapshots and JPEG extraction.
- External AI owns visual judgment and decision JSON only.
- Python owns decision validation, identity reconciliation, authorization,
  XMP mutation, evidence, checkpoint, and rollback.
- Decisions belong in `runtime/jobs/<job-id>/decisions/`.
- One prepared job contains photos from exactly one source folder.
- Every selected image receives exactly one terminal settlement record.

## Non-Negotiable Boundaries

- Never open or modify `.lrcat`, `.lrcat-wal`, or `.lrcat-shm`.
- Never write to `.lrdata`; read only through validated SQLite snapshots.
- Never modify RAW, NEF, JPEG originals, or EXIF capture fields.
- The only editable Lightroom development property is
  `crs:Exposure2012`.
- Never modify White Balance, Contrast, Highlights, Shadows, Whites, Blacks,
  Clarity, Texture, Vibrance, Saturation, Crop, Straighten, Masks, Keywords,
  Rating, Label, Sharpening, Noise Reduction, or export settings.
- Never delete or move user photographs.
- Reject outcomes remain suggestions only.
- Final export remains manual.
- Never store credentials or API keys in tracked files.
- Runtime jobs, previews, decisions, logs, XMP backups, and temp files must not
  be committed.

## XMP Rules

- Treat `crs:Exposure2012` as an EV value.
- `new_exposure = existing_exposure + validated_delta_ev`.
- A zero delta must not rewrite XMP.
- Require exact selection, full manifest, FOUND decision, UUID, RAW path, XMP
  path, and job identity reconciliation.
- Require exact source-folder containment for every real target.
- Missing, malformed, ambiguous, or multi-valued Exposure2012 fails closed for
  that image.
- Back up every real write and verify its SHA-256 against the original.
- Write through a validated temp file and atomic replace.
- Verify the target value and final hash after replacement.
- Roll back after post-write validation failure and verify the restored hash.
- Rollback failure is fatal and halts the batch.
- Checkpoint after every image; settled images must not be processed twice.

## AI Decision Rules

Every external AI task must use all four skills:

- `.agents/skills/exposure-judgment/SKILL.md`
- `.agents/skills/batch-consistency-review/SKILL.md`
- `.agents/skills/image-relevance-triage/SKILL.md`
- `.agents/skills/visual-quality-safety/SKILL.md`

The AI must:

- inspect the actual preview rather than infer from filenames;
- identify the intended subject and person priority;
- classify scene intent and preserve legitimate atmosphere;
- assess subject/background exposure and highlight/shadow safety;
- assess focus, blur, obstruction, accidental/test-shot evidence, relevance,
  duplicate/supporting value, and technical usability;
- group materially similar images and choose a reliable reference frame;
- preserve manifest order and return exactly one decision per FOUND image;
- recommend a bounded finite `delta_ev` and use `0.0` when no change is
  justified;
- return grounded KEEP, REVIEW, or SKIP decisions;
- never invent image IDs, paths, objects, or scene details.

AI output is untrusted input. Schema, exact-set identity, preview byte count,
and preview SHA-256 validation are mandatory before use.

## Seven Execution Rules

1. **Task Classification** — classify scope, risk level, affected capabilities,
   allowed files, forbidden files, and required evidence before editing.
2. **Define Done First** — record acceptance criteria and proof requirements
   before implementation.
3. **Parallel Evidence Gathering** — inspect repository truth, authority,
   tests, Git state, and runtime evidence before choosing a solution.
4. **Single Recommendation** — select one best bounded design; do not delegate
   routine technical decisions back to the owner.
5. **Surgical Change** — make the smallest complete change authorized by the
   active Work Order.
6. **Verify by Execution** — run focused, full, integration, syntax, diff, and
   status validation required by the Work Order. Reports alone are not proof.
7. **Outcome-First Reporting** — report implemented behavior, executed proof,
   Git scope, and remaining risk without unnecessary narration.

## Four Common AI Failure Modes

1. **Memory Over Repository Truth** — files, current HEAD, Git status, and
   executed evidence always override memory or prior summaries.
2. **Worker Reports Treated as Final Evidence** — inspect actual diffs,
   validation output, artifacts, and repository state.
3. **Leaving the Proof Chain Open** — no completion without acceptance,
   tests, documentation reconciliation, allowed scope, and current-work truth.
4. **Unauthorized Scope Expansion** — do not add unrelated refactors,
   frameworks, dependencies, features, or cleanup.

## Engineering and Git Rules

- Work on one bounded Work Order at a time.
- Do not redesign architecture outside explicit owner or Work Order authority.
- Prefer the Python standard library when practical.
- Add or update tests for every behavior change.
- Do not use broad staging such as `git add .`.
- Workers do not commit or push unless the active Work Order expressly permits
  it.
- Never commit runtime artifacts, previews, decisions, logs, XMP backups, or
  secrets.
- Do not claim `LIVE_VERIFIED` from code existence, static review, or synthetic
  tests.

## Required Preflight

Before editing, establish:

- active Work Order;
- affected capability IDs and current evidence level;
- allowed and forbidden files;
- expected behavior change;
- required validation;
- current Git status and HEAD;
- dry-run or real-write mode;
- exact safety boundary.

Unexpected changes, unresolved architecture conflict, unavailable required
proof, destructive action, credentials, or paid API use without owner approval
are stop conditions.

## Documentation and Knowledge Capture

`docs/INDEX.md` is the canonical document index. Every Work Order must review
and truthfully classify affected documents as `UPDATED`,
`REVIEWED_NO_CHANGE`, `NOT_APPLICABLE`, or `BLOCKED`.

Capture durable information needed by a future maintainer:

- behavior and architecture changed;
- why the selected design was accepted;
- invariants, ownership, configuration, and schema changes;
- validation actually executed;
- known limitations and remaining risks;
- decisions that must not be reopened without new evidence.

Do not record speculative narration or private reasoning. Prefer an existing
canonical document over a duplicate summary.

## Status-Truth Rules

- Code existence supports at most `IMPLEMENTED`.
- Passing focused tests supports at most `TESTED`.
- Cross-component validation supports `INTEGRATED`.
- Representative Lightroom Classic operation with real project data is
  required for `LIVE_VERIFIED`.
- Worker claims alone never promote capability status.
- Unknown evidence is recorded as unknown, not guessed.
- A status downgrade is allowed when evidence does not support the prior level.

## Completion Gate

A Work Order closes only when:

- acceptance criteria are satisfied;
- focused, full, and integration validation required by the Work Order pass;
- syntax/compile checks, `git diff --check`, and Git scope checks pass;
- forbidden files and runtime artifacts are absent from the diff;
- documentation impact review is complete;
- canonical documents match implemented truth;
- capability matrix, validation register, project status, active Work Order,
  and current-work pointer are reconciled;
- remaining risks are explicit;
- final Git state satisfies the Work Order closeout policy.

Code complete without documentation and evidence reconciliation is not
complete.

## Final Report

Report only:

- Work Order;
- files changed;
- behavior implemented;
- validation actually performed and results;
- documentation reviewed/updated;
- current Work Order status;
- remaining risks or stop condition;
- commit/branch/PR/push state.

Do not claim success without executed evidence.
