# WO-023: Manual Batch Provider and Evidence Contract

## Status
QUEUED

## Objective
Upgrade `manual_app` from a single-response-file seam into a deterministic batch provider with exact identity reconciliation and preserved provider evidence.

## Dependency
- WO-022 completed.

## Scope
- Replace `manual_response_file` with a response-directory or explicit response-map contract.
- Require exactly one response per FOUND manifest entry.
- Preserve provider metadata beside every decision.
- Reject incomplete, duplicate, missing, or unknown responses before analysis begins.

## Allowed Files
- `src/lr_ai_exposure/ai_judge.py`
- `src/lr_ai_exposure/providers/manual_app.py`
- `src/lr_ai_exposure/analysis_result.py`
- `src/lr_ai_exposure/analysis_artifacts.py`
- `tests/test_manual_batch_provider.py`
- `tests/test_analysis_artifacts.py`
- `Work-Order/WO-023-MANUAL-BATCH-PROVIDER-EVIDENCE-CONTRACT.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `docs/AI_JUDGE_CONTRACT.md`
- `docs/VALIDATION_REGISTER.md`

## Forbidden Changes
- No XMP apply or XMP writer changes.
- No network-provider redesign.
- No manual identity insertion after a response is generated.
- No RAW, catalog, or preview-cache mutation.

## Requirements
1. Replace single-file configuration with one of these canonical forms:
   - `manual_response_directory`, or
   - an explicit `image_id -> response_path` mapping.
2. Resolve exactly one JSON response for each FOUND manifest `image_id`.
3. Preflight exact set equality:
   - manifest FOUND IDs = response IDs.
4. Reject:
   - missing responses,
   - unknown responses,
   - duplicate IDs,
   - duplicate response files,
   - malformed JSON,
   - missing `image_id`,
   - response/manifest identity mismatch.
5. Do not system-bind a missing `image_id`; reject it.
6. Preserve manifest order in the returned records.
7. Introduce or use one canonical `AnalysisRecord` containing:
   - complete `SinglePassDecision`,
   - provider name,
   - model,
   - mode,
   - preview byte count,
   - preview SHA-256,
   - response reference,
   - token usage when available.
8. Write complete canonical artifacts without dropping risk or rationale fields.
9. Ensure response paths are contained within the authorized response directory.

## Acceptance Criteria
- A five-entry manifest consumes exactly five responses.
- Five unique decisions and five evidence records are returned.
- Decision order equals manifest order.
- Missing, duplicate, and unknown responses fail before partial processing.
- `image_id` is required in every manual response.
- No provider metadata is discarded.

## Validation
```powershell
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_manual_batch_provider.py tests/test_analysis_artifacts.py
env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/
git diff --check
git status --short
```

## Required Success Markers
```text
MANIFEST_RESPONSE_ID_SET_RECONCILED
MANUAL_RESPONSES_5
VALIDATED_DECISIONS_5
ANALYSIS_RECORDS_5
ORDER_PRESERVED
PROVIDER_METADATA_PRESERVED
UNKNOWN_RESPONSES_0
MISSING_RESPONSES_0
NO_XMP_MUTATION
```

## Stop Conditions
- Response identity cannot be reconciled exactly.
- A response can escape the authorized response directory.
- Partial batch success is silently accepted.
- Provider metadata cannot be serialized deterministically.

## Closeout
Commit once after all gates pass. Do not push unless explicitly authorized.
