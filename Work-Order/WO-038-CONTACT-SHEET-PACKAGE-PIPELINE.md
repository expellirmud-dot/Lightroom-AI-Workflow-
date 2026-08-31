# WO-038 — Contact Sheet Package Pipeline

STATUS: COMPLETE_LOCAL_VALIDATED

## Goal

Make Python automatically create exposure-only contact sheets during canonical
`Prepare AI Package` / `Prepare Next AI Package` preparation.  The immutable
pass package must contain ordered 4×4 sheets and an index before it reaches
`PACKAGE_READY`; an external AI only consumes those artifacts later.

## Phase 1 forensic decision — B

On 2026-08-31, the owner-specified pass
`runtime/sessions/sess-1788131769/passes/0001-pass-0001-20260830T231611Z`
was inspected read-only. `previews.db` and `root-pixels.db` both passed SQLite
`quick_check`. Ten evenly distributed selected images had exactly one
`RootPixels.jpegData` record each. The extracted output SHA-256 equalled that
payload; all decoded as baseline RGB JPEG 320×213 with the same quantization
tables. `PyramidLevel` metadata lists 960×640 and 1920×1281 tiers, but these
two snapshot DBs contain no corresponding JPEG blob or alternate RootPixels
record. Their `fileSize` values are metadata only; extracting them would
require reading cache files outside the authorized snapshots.

Decision: **B — retain the current 320px RootPixels JPEG extractor.** This WO
does not read any original `.lrdata` pyramid file or change preview selection.

## Scope

1. Validate each extracted `FOUND` JPEG through an actual Pillow decode before
   package construction; fail preparation closed when an expected preview is
   absent, corrupt, or its byte/SHA evidence disagrees.
2. Build contact sheets in Python from the validated extracted previews:
   - exactly 4 columns × 4 rows (at most 16 images per sheet);
   - preserve manifest `seq` order;
   - label every tile with the sequence number and short preview filename;
   - retain an incomplete final sheet;
   - write JPEG sheets under `contact_sheets/` and deterministic
     `contact-sheet-index.json` mapping each sheet to ordered image IDs and
     preview paths.
3. In the canonical preparation flow enforce this order:
   `snapshot → extract → validate previews → build contact sheets → write
   manifest/task/skills/schema/state → validate package → remove
   cache_snapshots → PACKAGE_READY`.
4. Package validation must prove the index/sheets map exactly to all `FOUND`
   manifest previews, preserve order, and leave no cache snapshot once the
   package is ready. Add index integrity to immutable package validation.
5. Update generated `AI_TASK.md`: use contact sheets first for batch context,
   sequence and relative brightness; open individual previews only when needed.
   The MVP task is exposure-only (`TOO_DARK`, `PASS`, `TOO_BRIGHT`, or
   `REVIEW`, translated to the existing decision schema). It may not judge or
   reject blur, focus, sharpness, damaged frames, duplicates, or relevance
   from these small previews.
6. Add focused automated tests and run the complete test suite. Do not call an
   AI provider.

## Allowed files

- `src/lr_ai_exposure/contact_sheets.py` (new)
- `src/lr_ai_exposure/session_lifecycle.py`
- `src/lr_ai_exposure/job_lifecycle.py`
- `tests/test_contact_sheets.py` (new)
- `tests/test_session_lifecycle.py`
- `tests/test_decoupled_package_workflow.py` only if an existing canonical
  package contract assertion requires extension
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `docs/AI_JUDGE_CONTRACT.md`
- `docs/DECISIONS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/PROJECT_STATUS.md`
- `README.md`
- `Work-Order/WO-038-CONTACT-SHEET-PACKAGE-PIPELINE.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

## Forbidden boundaries

- no Lightroom Catalog (`.lrcat`, WAL, SHM) access or mutation;
- no live `.lrdata` read beyond the existing read-only DB snapshot path and no
  `.lrdata` write;
- no RAW, JPEG original, XMP, metadata, or Develop mutation;
- no AI provider, network call, credentials, plugin menu change, or polling;
- no change to RootPixels preview extraction/selection as Phase 1 chose B;
- no commit of runtime packages, cache snapshots, contact sheets, previews,
  decisions, logs, or backups.

## Acceptance criteria

1. A 17-preview fixture produces two ordered 4×4 JPEG sheets with all labels,
   and the final sheet contains one tile; an index maps each sheet to exactly
   its expected IDs/preview paths.
2. Contact-sheet build refuses corrupt/missing/unverified preview inputs and
   package validation refuses a missing/tampered sheet or index mismatch.
3. Prepare outputs its manifest/task/skills/schema/state only after sheets
   exist; it removes the temporary `cache_snapshots` only after package
   validation succeeds; its returned/state package data exposes the contact
   sheet paths.
4. Generated task tells external AI to inspect contact sheets first and
   explicitly limits small-preview evaluation to exposure; it retains the
   existing strict decision schema and exactly one decision per `FOUND` image.
5. Existing canonical Prepare/Import/Prepare-Next separation remains true;
   preparation invokes no provider and does not mutate Lightroom/XMP/RAW.
6. Focused tests, full `pytest`, CLI configuration smoke test,
   `python -m compileall -q src tests`, `git diff --check`, and final Git scope
   inspection pass.

## Documentation impact

- `docs/FOLDER_JOB_WORKFLOW.md`, `docs/ARCHITECTURE.md`,
  `docs/AI_JUDGE_CONTRACT.md`, `docs/DECISIONS.md`, `README.md`: update.
- `docs/CAPABILITY_MATRIX.md`, `docs/VALIDATION_REGISTER.md`,
  `docs/PROJECT_STATUS.md`: reconcile at closeout with executed evidence only.
- `docs/XMP_SAFETY.md`, `docs/DIAGNOSTIC_PREFLIGHT.md`: REVIEWED_NO_CHANGE;
  this WO has no apply or diagnostic behavior change.

## Commit authority

No commit, push, or PR authority is granted by this Work Order.

## Completion evidence

- Phase 1 result: **B**. The authorized snapshots contained one 320px RootPixels
  JPEG payload per sampled image; no alternate high-resolution payload could be
  extracted without reading outside those snapshots.
- Implemented: Python preview decode/evidence validation, 4×4 ordered JPEG
  contact sheets, deterministic index, generated exposure-only AI task,
  immutable sheet/index verification at decision import, and cleanup of
  temporary snapshot DBs only after package validation.
- Validation: focused contact/session/CLI/plug-in regression (10 passed), full
  `python -m pytest -q`, `python -m compileall -q src tests`,
  `lr-ai-exposure --check-config`, and `git diff --check` all exited 0.
- Documentation: workflow, architecture, AI contract, decisions, capability,
  validation register, project status, and README updated; XMP safety and
  diagnostic preflight reviewed with no change.
- Remaining boundary: no representative Lightroom Classic package creation or
  external AI judgment was run. No commit, push, or PR was created.
