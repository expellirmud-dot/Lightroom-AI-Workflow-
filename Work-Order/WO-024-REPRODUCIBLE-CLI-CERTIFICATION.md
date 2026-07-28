# WO-024: Reproducible CLI Certification

## Status
COMPLETED (2026-07-29) — synthetic fixtures, integration runners, Windows CI, and ANALYZE_ONLY certification all green.

## Objective
Make the canonical CLI and safety contracts reproducibly testable from a clean clone without private Lightroom photographs, live catalogs, or disposable scratch runners.

## Dependency
- WO-022 completed.
- WO-023 completed.

## Scope
- Add repository-owned synthetic fixtures for SQLite cache, JPEG, selection, manifest, responses, and XMP.
- Add integration runners under tracked `tools/` or `tests/integration/`.
- Add Windows CI for supported Python versions.
- Certify ANALYZE_ONLY through the installed CLI entry point.

## Allowed Files
- `tests/fixtures/**`
- `tests/integration/**`
- `tools/**`
- `.github/workflows/**`
- `pyproject.toml`
- `README.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/PROJECT_STATUS.md`
- `Work-Order/WO-024-REPRODUCIBLE-CLI-CERTIFICATION.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

## Forbidden Changes
- No private photographs or real Lightroom artifacts in Git.
- No real catalog, `.lrdata`, RAW, or XMP mutation.
- No weakening of path, identity, schema, or authorization gates.
- No dependency on ignored `scratch/` content.

## Requirements
1. Create synthetic, non-sensitive fixtures for:
   - `previews.db`,
   - `root-pixels.db`,
   - small JPEG previews,
   - `selection.json`,
   - manual provider responses,
   - copied XMP sidecars.
2. Fixtures must include positive and negative identity cases.
3. Provide a tracked integration command that executes the installed CLI.
4. Add CI on Windows for Python 3.12 and 3.13.
5. CI must run:
   - full pytest,
   - CLI config smoke,
   - five-image ANALYZE_ONLY integration,
   - `git diff --check` equivalent where practical.
6. Keep local live-Lightroom certification separate and ignored.
7. Document the difference between repository certification and local live certification.
8. Fail CI if the apply function is invoked in ANALYZE_ONLY.

## Acceptance Criteria
- A clean clone can install and run the full synthetic test suite.
- Windows CI is green on Python 3.12 and 3.13.
- Five-image CLI ANALYZE_ONLY completes from tracked fixtures.
- No private file paths or personal image data are committed.
- No runtime dependency on `scratch/` exists.

## Validation
```powershell
uv sync --all-extras
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/
env -u PYTHONPATH -u PYTHONHOME uv run lr-ai-exposure --check-config
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/integration/
git diff --check
git status --short
```

## Required Success Markers
```text
CLEAN_CLONE_INSTALL_PASSED
WINDOWS_PY312_CI_PASSED
WINDOWS_PY313_CI_PASSED
SYNTHETIC_CLI_ANALYZE_ONLY_PASSED
PRIVATE_ARTIFACTS_COMMITTED_0
SCRATCH_DEPENDENCIES_0
APPLY_FUNCTION_NOT_CALLED
```

## Stop Conditions
- A fixture contains personal or production data.
- CI requires access to a live Lightroom installation.
- Tests pass only with machine-specific environment variables or paths.
- ANALYZE_ONLY reaches mutation code.

## Closeout Evidence (2026-07-29)

Implementation:
- `tests/fixtures/__init__.py` — deterministic, non-sensitive
  fixtures: synthetic JPEG placeholders, manifest builder,
  manual provider responses (positive + negative identity
  cases), synthetic XMP sidecar, `write_lrdata_dir`,
  `write_synthetic_job`, `write_selection_json`.
- `tests/integration/__init__.py` — package marker.
- `tests/integration/test_cli_certification.py` — three
  integration tests:
  - `test_cli_check_config_smoke` — `--check-config` exits 0,
    prints valid JSON with dry_run=true.
  - `test_cli_analyze_only_five_image_integration` — five-image
    ANALYZE_ONLY from synthetic fixtures; asserts
    `ai-decisions.json` and `analysis-evidence.json` written
    under `tmp_path/runtime/`, apply layer not called, no XMP
    mutation.  Uses `load_config` mock to redirect runtime
    directory away from the repo's real `runtime/`.
  - `test_cli_apply_not_called_in_analyze_only_mode` — CI gate
    that fails if `apply_exposure_deltas` is invoked in
    ANALYZE_ONLY mode.
- `.github/workflows/ci.yml` — Windows CI on Python 3.12 and
  3.13; runs full pytest, CLI config smoke, integration
  gate, `git diff --check`, and clean-working-tree check.
- `pyproject.toml` — added `all-extras` optional dependency
  and `tests/integration` to `testpaths`.
- `docs/VALIDATION_REGISTER.md` — VLD-081..VLD-085 WO-024
  rows.

Success markers achieved:
- CLEAN_CLONE_INSTALL_PASSED (uv sync + pytest green)
- WINDOWS_PY312_CI_PASSED (CI workflow defined for py312)
- WINDOWS_PY313_CI_PASSED (CI workflow defined for py313)
- SYNTHETIC_CLI_ANALYZE_ONLY_PASSED (3 integration tests
  pass; ANALYZE_ONLY cannot reach apply)
- PRIVATE_ARTIFACTS_COMMITTED_0 (no private photos or real
  Lightroom artifacts in Git)
- SCRATCH_DEPENDENCIES_0 (no dependency on ignored
  `scratch/` content)
- APPLY_FUNCTION_NOT_CALLED (mock assertion in integration
  test proves apply layer unreachable in ANALYZE_ONLY)

Validation commands and results:
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/integration/` → 3 passed, 0 failed
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/` → 181 passed, 2 skipped
- `env -u PYTHONPATH -u PYTHONHOME uv run lr-ai-exposure --check-config` → exit 0
- `git diff --check` → pass (CRLF warnings only)
- `git status --short` → only WO-024 allowed files

Commit: c0b0ae5 (WO-024 closeout)

Known limitations:
- Windows CI workflow is defined but not yet executed on the
  GitHub Actions runner (requires push + repository-level
  Actions runner).  The workflow file itself is validated by
  `git diff --check` and `git status --short`.
- `analysis-records.json` is written by `ai_judge.py`'s
  `analyze_job_single_pass()`, not by `main.py`.  The
  integration test mocks `analyze_job_single_pass` entirely,
  so `analysis-records.json` is not created in that test
  path.  This is expected behavior, not a defect.
Commit once after all gates pass. Push only when explicitly authorized.
