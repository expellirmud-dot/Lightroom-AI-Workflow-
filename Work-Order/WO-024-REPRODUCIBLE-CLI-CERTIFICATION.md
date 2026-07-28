# WO-024: Reproducible CLI Certification

## Status
QUEUED

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

## Closeout
Commit once after all gates pass. Push only when explicitly authorized.
