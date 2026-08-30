# AGENTS.md

## Project Mission

Build a Windows-first Lightroom Classic exposure assistant whose approved
target workflow is:

```text
diagnose exactly one Lightroom folder
→ start one provider-agnostic Exposure Session
→ capture an immutable Lightroom-rendered preview pass
→ external vision AI judges scene groups and exposure outliers
→ deterministic Python validates PASS / ADJUST / REVIEW decisions
→ explicitly apply guarded Exposure2012 changes
→ refresh Lightroom metadata and prove a new render generation
→ capture the next immutable pass and recheck unresolved images
→ stop at convergence, safe REVIEW, or another explicit stop condition
```

The application must remain independent of any single AI vendor or API.
Lightroom is the authoritative renderer. The MVP adjusts exposure only.

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

No active Work Order or conflicting authority is a stop condition. Dirty files
are classified by material risk under **Dirty Worktree Classification** below;
Git status alone is not a stop condition.

## Canonical Target Lifecycle

1. `DIAGNOSE_CURRENT_FOLDER` gathers independent Lightroom, eligibility,
   cache, runtime, CLI, bridge, and XMP-readiness evidence before creating a
   session. Diagnostics aggregate all discoverable issues rather than failing
   at the first independent check.
2. Lightroom requires exactly one active `LrFolder` and reads every directly
   contained proprietary-RAW master automatically; no Ctrl+A photo selection
   is required.
3. One Exposure Session freezes source-folder and image identity. Each analysis
   round is an immutable pass with monotonic `pass_number`, unique `pass_id`,
   and `parent_pass_id` pointing to the preceding pass or `null` for pass 1.
4. Each pass snapshots the preview cache read-only and records Lightroom-rendered
   preview identity, generation evidence, byte count, and SHA-256.
5. External vision AI judges intended subject, persistent scene groups,
   reference frames, outliers, and PASS / ADJUST / REVIEW. The canonical
   boundary is a provider-neutral file contract; optional adapters may use
   local models or APIs outside the core application.
6. Python validates identity, pass lineage, schema, confidence, pilot bounds,
   cumulative exposure, convergence, oscillation, and XMP authorization.
7. ADJUST applies only `crs:Exposure2012` through the existing guarded
   transaction. PASS and REVIEW never mutate XMP.
8. Lightroom refreshes metadata for `APPLIED_VERIFIED` images and remains the
   only authoritative renderer.
9. A subsequent pass is analyzable only after render freshness reconciles the
   expected Exposure2012, a new pass/generation identity, and refreshed preview
   evidence/hash. Preview hash alone is insufficient.
10. The session stops when no meaningful ADJUST remains, every unresolved image
    is REVIEW, a pilot limit is reached, or a safety condition fails closed.

The current source and plug-in still implement the WO-029 prepared-folder
single-pass lifecycle. Target documentation must label session/pass behavior
`PLANNED` until a separate implementation Work Order proves it.

## Runtime Ownership Rules

- Lightroom plug-in owns active-folder diagnostics, identity capture, session
  coordination, explicit apply invocation, source-folder confirmation,
  metadata refresh, and render-generation coordination.
- Cache extractor owns read-only SQLite snapshots and JPEG extraction.
- Session lifecycle owns immutable selection, pass lineage, self-contained
  skill/task/schema artifacts, generation evidence, and safe resume.
- External AI owns visual judgment and decision JSON only.
- Python owns decision validation, identity reconciliation, authorization,
  XMP mutation, evidence, checkpoint, and rollback.
- Decisions belong to one immutable pass beneath one session.
- One session contains eligible RAW masters from exactly one source folder.
- Every eligible RAW master receives exactly one settlement record per pass in
  which it is in scope and one terminal session outcome.

## Non-Negotiable Boundaries

- Never open or modify `.lrcat`, `.lrcat-wal`, or `.lrcat-shm`.
- Never write to `.lrdata`; read only through validated SQLite snapshots.
- Never modify RAW, NEF, JPEG originals, or EXIF capture fields.
- DNG, JPEG, TIFF, PSD, video, and virtual-copy inputs are outside the
  sidecar-only apply boundary and must not be prepared as writable targets.
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

## Session and Pass Integrity Rules

- A session freezes its source folder, eligible image identities, initial XMP
  evidence, and ordered group ledger.
- Every pass is self-contained and immutable after capture. It owns its
  manifest, Lightroom-rendered previews, task, bundled skills, decision schema,
  decisions, generation evidence, results, and apply evidence.
- `AI_SKILLS.md` is generated deterministically from all Markdown/JSON files in
  the four canonical visual skill directories.
- Missing canonical skill source files, task, schema, manifest, state,
  generation evidence, or session identity make processing fail closed.
- External AI may write only the pass-scoped decision output authorized by the
  file contract. It must not modify captured inputs.
- Apply must use the exact session/pass/source-folder lineage. A global response
  directory or mutable replacement pass is not canonical.
- Scene groups persist across passes by default. Conflicting evidence may move
  an image to REVIEW or create a provenance-recorded split; silent regrouping
  is forbidden.

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
- Before a later-pass write, reconcile the current XMP value and hash against
  the prior pass's verified final evidence.
- Metadata synchronization must fail closed when safe catalog/sidecar
  reconciliation cannot be proven. Do not require the owner to save metadata
  without evidence that synchronization is necessary.
- Numeric convergence and exposure bounds in target documents are pilot
  defaults, not production constants, until representative Lightroom evidence
  calibrates them.

## AI Decision Rules

Every captured target pass must bundle all content from these four skills.
Until session/pass implementation replaces WO-029, current prepared jobs retain
the same complete bundle requirement:

- `.agents/skills/exposure-judgment/`
- `.agents/skills/batch-consistency-review/`
- `.agents/skills/image-relevance-triage/`
- `.agents/skills/visual-quality-safety/`

The AI must:

- read `AI_TASK.md` and `AI_SKILLS.md` completely;
- inspect the actual preview rather than infer from filenames;
- identify the intended subject and person priority;
- classify scene intent and preserve legitimate atmosphere;
- assess subject/background exposure and highlight/shadow safety;
- assess focus, blur, obstruction, accidental/test-shot evidence, relevance,
  duplicate/supporting value, and technical usability;
- group materially similar images and choose a reliable reference frame;
- preserve manifest order and return exactly one decision per in-scope FOUND
  image for the current pass;
- recommend a bounded finite `delta_ev` and use `0.0` when no change is
  justified;
- return grounded PASS, ADJUST, or REVIEW decisions under the target contract;
- never invent image IDs, paths, objects, or scene details.

AI output is untrusted input. Schema, exact-set identity, session/pass lineage,
render-generation evidence, preview byte count, and preview SHA-256 validation
are mandatory before use.

## Seven Execution Rules

1. **Task Classification** — classify scope, risk level, affected capabilities,
   allowed files, forbidden files, and required evidence before editing.
2. **Define Done First** — record acceptance criteria and proof requirements
   before implementation.
3. **Bounded Evidence Gathering** — reuse a completed same-thread read-first
   preflight while its repository-truth fingerprints remain unchanged. After
   that, use delta preflight for HEAD, authority pointer, Git classification,
   and relevant-file status/hash.
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
- current Git status, dirty classification, and HEAD;
- dry-run or real-write mode;
- exact safety boundary.

Unresolved architecture conflict, unavailable required proof, destructive
action, credentials, or paid API use without owner approval are stop
conditions. Dirty state is handled by the classification below.

## Dirty Worktree Classification

Classify every dirty path before deciding whether work may continue:

- `NON_BLOCKING` — a pre-existing owner/local change is explicitly identified,
  unrelated to task files and proof, and can be preserved without edit,
  restore, stash, stage, commit, or accidental inclusion. Continue with an
  explicit exclusion.
- `BLOCKING` — a dirty path overlaps allowed task files, authority, generated
  proof, validation inputs, or the expected diff such that ownership or result
  attribution is ambiguous. Stop until resolved or the owner supplies a safe
  scoped decision.
- `CRITICAL` — dirty state indicates secrets, destructive or unauthorized
  mutation, corrupted safety evidence, catalog/cache/photo/XMP risk, or a state
  that cannot be preserved safely. Stop immediately.

Git status containing `M`, `A`, `D`, or `??` is evidence to classify, not by
itself a stop condition. Never overwrite, discard, stash, stage, or commit an
owner change without explicit authority.

## Read-First Reuse and Delta Preflight

A completed read-first/preflight in the same thread may be reused when HEAD,
active Work Order pointer, relevant authority files, and task context are
unchanged and remain available. Before each subsequent implementation step,
check only Git status/classification, HEAD, active Work Order pointer,
relevant-file status/hash, and Serena/CodeGraph availability when required.

Repeat full reads only when HEAD, active Work Order, a relevant file, tool
context, or available conversation context changed, or when repository policy
explicitly requires a fresh read. A material safety, correctness,
authorization, or proof risk is a stop condition; repeated reading without a
truth change is not.

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
