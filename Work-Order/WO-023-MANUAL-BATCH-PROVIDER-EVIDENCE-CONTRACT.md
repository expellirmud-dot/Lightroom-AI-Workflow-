# WO-023: Manual Batch Provider and Evidence Contract

## Status
COMPLETED (2026-07-28) — deterministic batch provider with exact identity reconciliation and canonical AnalysisRecord evidence contract.

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

## Closeout Evidence (2026-07-28)

Implementation:
- `src/lr_ai_exposure/analysis_artifacts.py` — new canonical owner of
  `AnalysisRecord` (complete `SinglePassDecision` + provider evidence:
  provider, model, mode, preview bytes, preview SHA-256, response
  reference, token usage). Atomic writes via temp-file + replace.
- `src/lr_ai_exposure/providers/manual_app.py` — replaced single-file
  `manual_response_file` seam with `manual_response_directory` batch
  contract. Added `resolve_manual_response_map()` which performs exact
  set equality between manifest FOUND IDs and response IDs before any
  analysis begins. Missing, unknown, duplicate, malformed, and
  missing-`image_id` responses are rejected (no system-binding).
  Response path containment enforced against the authorized directory.
- `src/lr_ai_exposure/ai_judge.py` — `analyze_job_single_pass()` now
  calls `resolve_manual_response_map()` for `manual_app` provider,
  collects one `AnalysisRecord` per decision in manifest order, and
  writes `analysis-records.json` atomically into the job directory.
  The `manual_response_file` config key is retired for `manual_app`.
- `tests/test_manual_batch_provider.py` — 12 new tests covering the
  batch preflight rejection matrix (missing/unknown/duplicate/malformed/
  missing-id/duplicate-manifest-id/non-directory/symlink-escape) and
  the 5-entry end-to-end acceptance (MANIFEST_RESPONSE_ID_SET_RECONCILED,
  MANUAL_RESPONSES_5, VALIDATED_DECISIONS_5, ANALYSIS_RECORDS_5,
  ORDER_PRESERVED, PROVIDER_METADATA_PRESERVED).
- `tests/test_analysis_artifacts.py` — 9 new tests covering the
  `AnalysisRecord` contract (full schema preserved, provider metadata
  preserved, token_usage optional, extra-field rejection, negative
  preview_bytes rejection, deterministic serialization, atomic write).

Validation performed (all rc=0):
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q
  tests/test_manual_batch_provider.py tests/test_analysis_artifacts.py`
  — **21 passed, 0 failed** (focused WO-023 suite).
- `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/`
  — **178 passed, 2 skipped** (pre-existing skips, unchanged).
- `git diff --check` — clean (CRLF warnings only; pre-existing repo policy).
- `git status --short` — only WO-023 allowed files changed.

Success markers:
- MANIFEST_RESPONSE_ID_SET_RECONCILED — confirmed (set equality
  enforced in `resolve_manual_response_map`; 5-entry manifest = 5
  responses).
- MANUAL_RESPONSES_5 — confirmed (5 decisions returned for 5-entry
  manifest).
- VALIDATED_DECISIONS_5 — confirmed (full `SinglePassDecision` schema
  preserved in `analysis-records.json`).
- ANALYSIS_RECORDS_5 — confirmed (`analysis-records.json` written with
  `record_count=5`, manifest order).
- ORDER_PRESERVED — confirmed (record index matches manifest entry
  order; `delta_ev` tracks `seq`).
- PROVIDER_METADATA_PRESERVED — confirmed (provider, model, mode,
  preview_bytes, preview_sha256, response_reference all present;
  `token_usage` carried when available).
- UNKNOWN_RESPONSES_0 — confirmed (unknown response IDs rejected
  before processing).
- MISSING_RESPONSES_0 — confirmed (missing FOUND manifest IDs rejected
  before processing).
- NO_XMP_MUTATION — confirmed (no XMP writer touched; `apply.py` not
  imported; ANALYZE_ONLY path proven unable to reach apply layer;
  `analysis-records.json` contains no XMP data).
Commit once after all gates pass. Do not push unless explicitly authorized.
