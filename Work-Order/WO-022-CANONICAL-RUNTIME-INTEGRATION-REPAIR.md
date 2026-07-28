# WO-022: Canonical Runtime Integration Repair

## Status
QUEUED

## Objective
Make the repository's canonical `lr-ai-exposure` CLI execute a complete, reproducible ANALYZE_ONLY workflow without relying on bespoke `scratch/` runners.

## Dependency
- WO-020 = `ANALYZE_ONLY_PILOT_COMPLETED`
- WO-021 = `COMPLETED_WITH_GOOGLE_API_QUOTA_BLOCKED`

## Scope
- Repair the canonical CLI call graph.
- Make ANALYZE_ONLY the default execution mode.
- Pass the validated settings object through analysis and apply boundaries.
- Prevent the apply layer from being invoked during ANALYZE_ONLY.
- Write complete decision artifacts through the product entry point.

## Allowed Files
- `src/lr_ai_exposure/main.py`
- `src/lr_ai_exposure/ai_judge.py`
- `src/lr_ai_exposure/config.py`
- `src/lr_ai_exposure/analysis_result.py`
- `tests/test_main_integration.py`
- `tests/test_cli_modes.py`
- `Work-Order/WO-022-CANONICAL-RUNTIME-INTEGRATION-REPAIR.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/ARCHITECTURE.md` only if the runtime flow changes materially

## Forbidden Changes
- No XMP writer changes.
- No real XMP apply.
- No RAW, catalog, or preview-cache mutation.
- No changes to Lightroom databases except existing read-only access.
- No creation of a second manifest or decision model.

## Requirements
1. Add explicit CLI modes:
   - `--analyze-only`
   - `--apply`
2. Default to ANALYZE_ONLY when neither mode is supplied.
3. Call:
   - `analyze_job_single_pass(manifest, job_dir, settings)`
   - `apply_exposure_deltas(job_dir, selection_path, decisions, settings)`
4. Never call `apply_exposure_deltas` in ANALYZE_ONLY mode.
5. Write full `SinglePassDecision` schema using `model_dump(mode="json")`.
6. Write canonical artifacts under the job directory:
   - `ai-decisions.json`
   - `analysis-evidence.json`
7. Preserve manifest order.
8. Return non-zero on handoff, analysis, artifact, or apply failure.
9. Eliminate all current signature mismatches.

## Acceptance Criteria
- Canonical CLI completes a synthetic five-image ANALYZE_ONLY workflow.
- `CLI_EXIT=0`.
- Five decisions are written in manifest order.
- Full risk and rationale fields are preserved.
- Apply function is proven not called.
- No XMP, RAW, catalog, or preview-cache mutation occurs.

## Validation
```powershell
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/
env -u PYTHONPATH -u PYTHONHOME uv run lr-ai-exposure --check-config
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_main_integration.py tests/test_cli_modes.py
git diff --check
git status --short
```

## Required Success Markers
```text
CANONICAL_CLI_EXIT_0
ANALYZE_ONLY_DEFAULT_CONFIRMED
VALIDATED_DECISIONS_5
FULL_DECISION_SCHEMA_WRITTEN
ANALYSIS_EVIDENCE_WRITTEN
APPLY_FUNCTION_NOT_CALLED
NO_XMP_MUTATION
```

## Stop Conditions
- More than one canonical manifest or decision model is discovered.
- ANALYZE_ONLY can reach the apply layer.
- Canonical CLI requires untracked `scratch/` code.
- Any real file mutation outside the runtime job directory.

## Closeout
Commit once after all gates pass. Do not push unless explicitly authorized.
