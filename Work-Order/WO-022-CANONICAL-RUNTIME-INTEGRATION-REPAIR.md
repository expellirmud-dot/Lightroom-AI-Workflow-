# WO-022: Canonical Runtime Integration Repair

## Status
COMPLETED (2026-07-28, governance remediation) — ANALYZE_ONLY canonical CLI
repair. Apply layer never reached in default mode. Original closeout commit
d1deda1 was rejected for governance violations (preflight READY with untracked
`.zcode/`; Serena project mismatch with canonical Git root; `tests/test_main.py`
modified outside the then-current Allowed Files). Commit d1deda1 was undone via
`git reset --mixed` with all changes preserved, the Allowed Files list was
amended, preflight was repeated cleanly, full validation was re-executed, and a
single new authorized commit closed the Work Order. No push.

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
- `tests/test_main.py` — amended into scope during governance remediation.
  Rationale: The existing canonical main-flow test encoded the pre-WO-022
  behavior that always called the apply layer. Updating the test is required
  to prove the new default ANALYZE_ONLY contract and eliminate stale
  signature assertions.
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

## Closeout Evidence (2026-07-28)

Implementation:
- `src/lr_ai_exposure/main.py` — added `--analyze-only`/`--apply` modes
  (default ANALYZE_ONLY), passed the validated `settings` object through
  the analysis and apply boundaries, made the apply import lazy so the
  default path cannot reach `apply_exposure_deltas`, and routed artifact
  writing through the new `analysis_result` module.
- `src/lr_ai_exposure/analysis_result.py` — new canonical owner of
  `ai-decisions.json` (full `SinglePassDecision.model_dump(mode="json")`
  in manifest order) and `analysis-evidence.json` (mode, provider, model,
  identity chain, markers). Atomic writes via temp-file + replace.
- Signature mismatches eliminated: `analyze_job_single_pass(manifest,
  job_dir, settings)` and `apply_exposure_deltas(job_dir, selection_path,
  decisions, settings)` are now called with their real signatures.

Validation performed (all rc=0):
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/` — full suite
  green (2 pre-existing skips consistent with baseline).
- `env -u PYTHONPATH -u PYTHONHOME uv run lr-ai-exposure --check-config`
  — exit 0, summary printed.
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_main_integration.py
  tests/test_cli_modes.py` — 10 passed, 0 failed.
- `git diff --check` — clean (CRLF warnings only; pre-existing repo policy).
- `git status --short` — only WO-022 allowed files changed.

Success markers:
- CANONICAL_CLI_EXIT_0 — confirmed (rc=0 in integration test).
- ANALYZE_ONLY_DEFAULT_CONFIRMED — confirmed (`_select_mode([]) ==
  "ANALYZE_ONLY"`; default-mode test asserts apply not called).
- VALIDATED_DECISIONS_5 — confirmed (synthetic 5-image manifest).
- FULL_DECISION_SCHEMA_WRITTEN — confirmed (all 11 schema fields asserted
  in ai-decisions.json).
- ANALYSIS_EVIDENCE_WRITTEN — confirmed (analysis-evidence.json present
  with identity chain + markers).
- APPLY_FUNCTION_NOT_CALLED — confirmed (mock at
  `lr_ai_exposure.apply.apply_exposure_deltas` asserts not called in
  ANALYZE_ONLY; apply import is lazy).
- NO_XMP_MUTATION — confirmed (no XMP writer touched; ANALYZE_ONLY path
  proven unable to reach apply layer).

Remaining risks:
- Google Vision API remains quota-blocked (inherited from WO-021); live
  ANALYZE_ONLY against real previews still requires manual_app provider
  or restored quota. This is unchanged by WO-022.
- `apply.py` retains a duplicate import block (cosmetic) — left untouched
  because apply.py is outside WO-022 allowed files.

Files changed:
- `src/lr_ai_exposure/main.py`
- `src/lr_ai_exposure/analysis_result.py` (new)
- `tests/test_main.py`
- `tests/test_main_integration.py` (new)
- `tests/test_cli_modes.py` (new)
- `docs/ARCHITECTURE.md` (runtime-flow + project layout)
- `docs/VALIDATION_REGISTER.md` (evidence rows)
- `Work-Order/CURRENT_WORK_ORDER.md` (pointer reconciliation)
- `Work-Order/WO-022-CANONICAL-RUNTIME-INTEGRATION-REPAIR.md` (this section)

## Governance Remediation Record (2026-07-28)

Rejected closeout commit: `d1deda1` (undone with `git reset --mixed HEAD~1`;
all implementation content preserved in the working tree).

Violations remediated:
1. Preflight had declared READY while untracked `.zcode/` existed.
   Resolution: `.zcode/` inspected — 1 KB disposable editor hook-config state
   (`config.json` with `hooks.enabled=false` only). Added to local
   `.git/info/exclude` (NOT tracked `.gitignore`, which was not separately
   authorized). `git status` now contains no unexpected paths.
2. Serena project did not match the canonical Git root.
   Resolution: Serena re-activated for exactly
   `D:\ai-tools\lightroom-ai-exposure` and verified via `get_current_config`
   (active project `lightroom-ai-exposure` at that exact path).
3. `tests/test_main.py` was modified without being listed in Allowed Files.
   Resolution: Allowed Files amended (see rationale in the Allowed Files
   section). The test rewrite proves the default ANALYZE_ONLY contract and
   removes stale pre-WO-022 signature assertions that required apply to be
   called.

CodeGraph verified for the same exact root (`.codegraph/codegraph.db`
resolved live source for `main`, `_run_analysis`, `analyze_job_single_pass`,
`apply_exposure_deltas`).

Re-validation (single clean sequence, all rc=0):
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/` —
  157 passed, 2 skipped (pre-existing skips).
- `env -u PYTHONPATH -u PYTHONHOME uv run lr-ai-exposure --check-config` —
  exit 0, summary printed.
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q
  tests/test_main_integration.py tests/test_cli_modes.py` — 10 passed.
- `git diff --check` — clean (CRLF warnings only; pre-existing repo policy).
- `git status --short` — only amended WO-022 Allowed Files changed.

No XMP, RAW, catalog, or preview-cache file was touched during remediation.
Push was not performed.
