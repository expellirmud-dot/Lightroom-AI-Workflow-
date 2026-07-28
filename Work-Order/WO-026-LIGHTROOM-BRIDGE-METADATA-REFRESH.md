# WO-026: Lightroom Bridge and Metadata Refresh

## Status
COMPLETED (2026-07-29)

## Objective
Connect the proven Python workflow to a thin Lightroom bridge that performs selection handoff, launches the canonical CLI, reports results, and refreshes Lightroom metadata after an authorized apply.

## Dependency
- WO-022 completed.
- WO-023 completed.
- WO-024 completed.
- WO-025 completed with one-image apply and rollback proof.

## Scope
- Keep Lightroom plugin responsibilities thin.
- Export only selected-photo identity and approved paths.
- Launch the canonical CLI with explicit mode and job identity.
- Read result artifacts and display bounded status.
- Refresh metadata only after `APPLIED_VERIFIED`.

## Allowed Files
- Lightroom plugin source and manifest files under the repository's plugin directory.
- `src/lr_ai_exposure/main.py`
- bridge protocol models and tests.
- `tests/test_lightroom_bridge_contract.py`
- `tests/test_metadata_refresh_gate.py`
- `tests/test_lightroom_plugin.py` (amended: requires adaptation for authorized CLI launch)
- `docs/ARCHITECTURE.md`
- `README.md`
- `docs/VALIDATION_REGISTER.md`
- `Work-Order/WO-026-LIGHTROOM-BRIDGE-METADATA-REFRESH.md`
- `Work-Order/CURRENT_WORK_ORDER.md`

## Forbidden Changes
- No AI logic in the Lightroom plugin.
- No direct plugin access to SQLite preview databases.
- No plugin-side XMP mutation.
- No RAW or catalog mutation.
- No metadata refresh for failed, skipped, proposed, or rolled-back results.

## Bridge Responsibilities
### Lightroom Plugin
- Read current selection identity.
- Write bounded `selection.json`.
- Launch the canonical CLI.
- Display progress and terminal result.
- Refresh metadata for exact verified targets only.

### Python Runtime
- Own cache access, preview extraction, provider analysis, validation, apply transaction, rollback, and evidence.

## Requirements
1. Define a versioned bridge contract containing:
   - protocol version,
   - job ID,
   - selected count,
   - ordered photo identities,
   - requested mode,
   - result artifact path.
2. Reject unsupported protocol versions.
3. Prevent duplicate concurrent launches for the same job.
4. Require exact terminal state before refresh.
5. Refresh only IDs with `APPLIED_VERIFIED`.
6. Never refresh metadata for `FAILED_*`, `ROLLED_BACK`, `SKIPPED`, or `PROPOSED`.
7. Surface actionable errors without exposing secrets.
8. Preserve ANALYZE_ONLY as a non-mutating workflow.
9. Add cancellation and process-settlement handling.

## Acceptance Criteria
- Lightroom selection creates a valid ordered handoff.
- Canonical CLI is launched with the expected mode and job ID.
- ANALYZE_ONLY returns decisions without metadata refresh.
- One-image authorized apply returns `APPLIED_VERIFIED` and triggers refresh for exactly one photo.
- Failure and rollback paths trigger no refresh.
- No plugin-side database or XMP mutation exists.

## Validation
```powershell
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_lightroom_bridge_contract.py tests/test_metadata_refresh_gate.py
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/
git diff --check
git status --short
```

## Required Success Markers
```text
BRIDGE_PROTOCOL_VERSION_VERIFIED
SELECTION_ORDER_PRESERVED
CANONICAL_CLI_LAUNCHED
ANALYZE_ONLY_REFRESH_COUNT_0
APPLIED_VERIFIED_REFRESH_COUNT_1
FAILED_RESULT_REFRESH_COUNT_0
PLUGIN_XMP_MUTATION_0
PLUGIN_CACHE_DB_ACCESS_0
```

## Stop Conditions
- Plugin must perform AI, cache, or XMP work to continue.
- Result identity cannot be reconciled to the Lightroom selection.
- Metadata refresh behavior cannot be limited to exact verified targets.
- CLI process settlement is ambiguous.

## Closeout
Commit once after all gates pass. Do not expand batch size in this Work Order. Push only when explicitly authorized.
