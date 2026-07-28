# Validation Register

Canonical executed-evidence register for the Lightroom AI Exposure project.

## Evidence Types

- **Automated test evidence** — pytest results
- **Static or syntax validation** — compileall, type checks
- **Git/diff scope validation** — git diff --check, git status --short
- **Integration validation** — cross-component workflow checks
- **Live Lightroom validation** — real Lightroom Classic + real project data

## Executed Evidence

### WO-001 (Project Scaffold) — commit a7228cc

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-001 | 2026-07-28 | pytest suite | `pytest -q` | 10 passed, 0 failed | src/ and tests/ | WO-001 | a7228cc |
| VLD-002 | 2026-07-28 | Syntax check | `compileall -q src` | pass | src/lr_ai_exposure/ | WO-001 | a7228cc |
| VLD-003 | 2026-07-28 | Config check | `python -m lr_ai_exposure.main --check-config` | exit 0 | Config validation | WO-001 | a7228cc |
| VLD-004 | 2026-07-28 | Diff check | `git diff --check` | pass | All staged files | WO-001 | a7228cc |
| VLD-005 | 2026-07-28 | Git scope | `git status --short` | clean except allowed files | Only WO-001 allowed files changed | WO-001 | a7228cc |

### WO-002 (Documentation Governance) — commit 192a5e6

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-006 | 2026-07-28 | Git diff check | `git diff --check` | pass (CRLF normalization warning on .gitignore only) | Allowed docs and AGENTS.md | WO-002 | 192a5e6 |
| VLD-007 | 2026-07-28 | Git scope | `git status --short` | clean after commit | 4 WO-002 allowed files committed | WO-002 | 192a5e6 |

### WO-003 (Traceability Registers) — in progress

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-008 | 2026-07-28 | Docs exist | File existence check | PASS | PROJECT_STATUS.md CAPABILITY_MATRIX.md VALIDATION_REGISTER.md | WO-003 | pending |
| VLD-009 | 2026-07-28 | Status names | Grep test in CAPABILITY_MATRIX.md | Pending | All 9 status names must be present | WO-003 | pending |
| VLD-010 | 2026-07-28 | Capability IDs | Count from CAP-001 through CAP-014 | Pending | Exactly 14 capabilities | WO-003 | pending |
| VLD-011 | 2026-07-28 | INDEX.md includes | Grep for new docs | Pending | All three new docs listed | WO-003 | pending |
| VLD-012 | 2026-07-28 | AGENTS.md traceability | Grep for Project Traceability | Pending | Traceability section present | WO-003 | pending |
| VLD-013 | 2026-07-28 | Git scope | `git diff --check` | Pending | Only allowed files changed | WO-003 | pending |
| VLD-014 | 2026-07-28 | CURRENT_WORK_ORDER.py terminal | Read CURRENT_WORK_ORDER.md | Pending | STATUS: NONE after closeout | WO-003 | pending |

### WO-004 (Project Read-First Skill) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-015 | 2026-07-28 | pytest suite | `pytest -q` | 18 passed, 0 failed | .agents/skills/ and tests/ | WO-004 | pending |
| VLD-016 | 2026-07-28 | Syntax check | `compileall -q src` | pass | src/lr_ai_exposure/ | WO-004 | pending |
| VLD-017 | 2026-07-28 | Diff check | `git diff --check` | pass | All staged files | WO-004 | pending |
| VLD-018 | 2026-07-28 | Git scope | `git status --short` | clean after commit | Only allowed files changed | WO-004 | pending |

### WO-005 (Job and Manifest Foundation) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-019 | 2026-07-28 | pytest job suite | `pytest -q tests/test_job.py` | 16 passed, 0 failed | src/lr_ai_exposure/job.py and tests/ | WO-005 | pending |
| VLD-020 | 2026-07-28 | pytest full suite | `pytest -q` | 34 passed, 0 failed | src/ and tests/ | WO-005 | pending |
| VLD-021 | 2026-07-28 | Syntax check | `compileall -q src` | pass | src/lr_ai_exposure/ | WO-005 | pending |
| VLD-022 | 2026-07-28 | Diff check | `git diff --check` | pass (CRLF warning only) | All staged files | WO-005 | pending |
| VLD-023 | 2026-07-28 | Git scope | `git status --short` | clean after commit | Only allowed files changed | WO-005 | pending |

### WO-006 (Lightroom Plugin Skeleton) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-024 | 2026-07-28 | pytest plugin contract | `pytest -q tests/test_lightroom_plugin_contract.py` | 6 passed (1 Lua-parse skip), 0 failed | lightroom-plugin/ and tests/ | WO-006 | pending |
| VLD-025 | 2026-07-28 | pytest full suite | `pytest -q` | 41 passed (1 skip), 0 failed | src/ and tests/ | WO-006 | pending |
| VLD-026 | 2026-07-28 | Syntax check | `compileall -q src` | pass | src/lr_ai_exposure/ | WO-006 | pending |
| VLD-027 | 2026-07-28 | Diff check | `git diff --check` | pass (CRLF warning only) | All staged files | WO-006 | pending |
| VLD-028 | 2026-07-28 | Git scope | `git status --short` | clean after commit | Only allowed files changed | WO-006 | ffd57f5 |

### WO-007 (Preview Export and Manifest Handoff) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-029 | 2026-07-28 | pytest WO-007 contract | `pytest -q tests/test_preview_export_handoff.py` | 6 passed, 0 failed | lightroom-plugin/RunExposureAssist.lua + tests/ | WO-007 | pending |
| VLD-030 | 2026-07-28 | pytest full suite | `pytest -q` | 47 passed (1 skip), 0 failed | src/ and tests/ | WO-006+007 | pending |
| VLD-031 | 2026-07-28 | Syntax check | `compileall -q src` | pass | src/lr_ai_exposure/ | WO-007 | pending |
| VLD-032 | 2026-07-28 | Diff check | `git diff --check` | pass (CRLF warning only) | All staged files | WO-007 | pending |
| VLD-033 | 2026-07-28 | Git scope | `git status --short` | clean after commit | Only allowed files changed | WO-007 | pending |

### WO-008 (Preview Validation) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-034 | 2026-07-28 | pytest WO-008 | pytest -q tests/test_preview.py | 8 passed, 0 failed | src/lr_ai_exposure/preview.py + tests/ | WO-008 | pending |
| VLD-035 | 2026-07-28 | pytest full suite | pytest -q | 53 passed (1 skip), 0 failed | src/ and tests/ | WO-008 | pending |
| VLD-036 | 2026-07-28 | Syntax check | compileall -q src | pass | src/lr_ai_exposure/ | WO-008 | pending |

### WO-009 (AI Decision Contract and Mock Judge) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-037 | 2026-07-28 | pytest WO-009 | pytest -q tests/test_judge.py | 15 passed, 0 failed | src/lr_ai_exposure/judge.py + tests/ | WO-009 | pending |
| VLD-038 | 2026-07-28 | pytest full suite | pytest -q | 68 passed (1 skip), 0 failed | src/ and tests/ | WO-009 | pending |
| VLD-039 | 2026-07-28 | Syntax check | compileall -q src | pass | src/lr_ai_exposure/ | WO-009 | pending |

### WO-010.1 (Exposure Judgment) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-040 | 2026-07-28 | pytest WO-010.1 | pytest -q tests/test_exposure_judgment.py tests/test_batch_consistency.py | 15 passed, 0 failed | src/lr_ai_exposure/ + tests/ | WO-010.1 | pending |
| VLD-041 | 2026-07-28 | Syntax check | compileall -q src | pass | src/lr_ai_exposure/ | WO-010.1 | pending |

### WO-010.2 (Image Relevance and Quality Triage) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-042 | 2026-07-28 | pytest WO-010.2 | `pytest -q tests/test_image_triage.py tests/test_quality_safety.py` | 13 passed, 0 failed | src/lr_ai_exposure/ + tests/ | WO-010.2 | pending |
| VLD-043 | 2026-07-28 | Syntax check | `compileall -q src` | pass | src/lr_ai_exposure/ | WO-010.2 | pending |

### WO-010 (XMP Read and Backup) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-044 | 2026-07-28 | pytest WO-010 | pytest -q tests/test_xmp.py | 7 passed, 0 failed | src/lr_ai_exposure/xmp.py + tests/ | WO-010 | pending |
| VLD-045 | 2026-07-28 | Syntax check | compileall -q src | pass | src/lr_ai_exposure/ | WO-010 | pending |

### WO-011 (Exposure2012 Safe Write) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-046 | 2026-07-28 | pytest WO-011 | pytest -q tests/test_xmp.py | 12 passed, 0 failed | src/lr_ai_exposure/xmp.py + tests/ | WO-011 | pending |

### WO-012 (End-to-End Dry-Run Integration) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-047 | 2026-07-28 | pytest WO-012 | pytest -q tests/test_main.py | 1 passed, 0 failed | src/lr_ai_exposure/main.py + tests/ | WO-012 | pending |

### WO-015 (Lightroom Preview Cache Identity Mapping) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-048 | 2026-07-28 | pytest WO-015 | pytest -q tests/test_cache_probe.py | 4 passed, 0 failed | src/lr_ai_exposure/cache_probe.py + tests/ | WO-015 | 52431b5 |
| VLD-049 | 2026-07-28 | Syntax check | compileall -q src | pass | src/lr_ai_exposure/ | WO-015 | 52431b5 |
| VLD-050 | 2026-07-28 | E2E probe run | python scratch/run_remediation_probe.py | pass, jpeg written | Real Lightroom cache DBs | WO-015 | 52431b5 |

### WO-016 (Read-Only Cache Preview Extractor) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-051 | 2026-07-28 | pytest WO-016 | pytest -q tests/test_cache_extractor.py | 2 passed, 0 failed | src/lr_ai_exposure/cache_extractor.py + tests/ | WO-016 | 9eb9ff1 |
| VLD-052 | 2026-07-28 | Live Batch 10 | python scratch/test_batch_extract.py | 10/10 FOUND, JPEGs saved | Real Lightroom cache DBs | WO-016 | 9eb9ff1 |

### WO-017 (Cache Preview Job Manifest Handoff) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-053 | 2026-07-28 | pytest WO-017 | pytest -q tests/test_job.py tests/test_handoff.py | 17 passed, 0 failed | src/lr_ai_exposure/ + tests/ | WO-017 | cb81951 |
| VLD-054 | 2026-07-28 | Live Batch 25 | python scratch/test_job_handoff.py | 25/25 FOUND, Manifest OK | Real Lightroom cache DBs | WO-017 | cb81951 |

### WO-018 (Single-Pass AI Triage and Exposure Judgment) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-055 | 2026-07-28 | pytest WO-018 | pytest -q tests/test_apply.py | 1 passed, 0 failed | src/lr_ai_exposure/ai_judge.py + tests | WO-018 | 879aabf |
| VLD-056 | 2026-07-28 | Syntax check | python -m compileall -q src | pass | src/ | WO-018 | 879aabf |

### WO-019 (Guarded XMP Exposure Apply Pilot) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-057 | 2026-07-28 | pytest WO-019 | pytest -q tests/test_apply.py tests/test_config.py | passed | src/lr_ai_exposure/apply.py + tests | WO-019 | 40607c3 |
| VLD-058 | 2026-07-28 | Pilot Batch 1 | python -m pytest -q tests/test_main.py | passed | Real Lightroom cache DBs | WO-019 | 40607c3 |

### WO-REMEDIATION (Phase D & E) — commit pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-059 | 2026-07-28 | pytest suite | `pytest -q tests/` | 55 passed, 1 skipped | src/ and tests/ | REMEDIATION | pending |
| VLD-060 | 2026-07-28 | Copied-XMP Pilot | `python scratch/pilot_phase_e.py` | pass, verified rollback SHA256 | XMP rollback integration | REMEDIATION | pending |


### WO-021 (Vision Provider Integration)

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-061 | 2026-07-28 | pytest WO-021 | `pytest -q tests/` | 138 passed, 2 skipped | src/lr_ai_exposure/providers/ + tests | WO-021 | 9cd6a4c |
| VLD-062 | 2026-07-28 | Live Google API | `python scratch/run_live_cert.py` | LIVE_VISION_REQUEST_ATTEMPTED, QUOTA_EXHAUSTED | Google Vision Provider | WO-021 | 9cd6a4c |
| VLD-063 | 2026-07-28 | Manual Provider | `python scratch/run_manual_cert.py` | JPEG_IDENTITY_VERIFIED, CANONICAL_LIGHTROOM_IDENTITY_RECONCILED, MANUAL_DECISION_SCHEMA_VALID, NO_XMP_MUTATION | NON_REPRODUCIBLE_LOCAL_EVIDENCE | WO-021 | 9cd6a4c |


| VLD-064 | 2026-07-28 | WO-020 cache-probe regression | `uv run pytest -q tests/test_cache_probe_bounded.py` | 8 passed | tests/test_cache_probe_bounded.py (tmp_path only) | WO-020 | 9cd6a4c |
| VLD-065 | 2026-07-28 | WO-020 full suite | `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/` | TESTS_EXIT=0 (clean) | tests/ | WO-020 | 9cd6a4c |
| VLD-066 | 2026-07-28 | WO-020 canonical extraction | `uv run python scratch/prepare_wo020_canonical.py` | CANONICAL_IMAGES=5; 5 UUIDs, 5 byte counts, 5 SHA-256 | scratch/wo020_canonical_identity.json | WO-020 | 9cd6a4c |
| VLD-067 | 2026-07-28 | WO-020 pilot run | `uv run python scratch/run_wo020_pilot.py` | MANUAL_RESPONSES=5, VALIDATED_DECISIONS=5, ai-decisions.json written | scratch/wo020_job/ai-decisions.json | WO-020 | 9cd6a4c |
| VLD-068 | 2026-07-28 | WO-020 ANALYZE_ONLY guard | manual inspection of ai-decisions.json | apply_authorized=False, xmp_mutation=False, no apply_exposure_deltas | scratch/wo020_job/ai-decisions.json | WO-020 | 9cd6a4c |


### WO-022 (Canonical Runtime Integration Repair)

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-069 | 2026-07-28 | Full pytest suite | `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/` | TESTS_EXIT=0 (2 pre-existing skips) | src/lr_ai_exposure/ + tests/ | WO-022 | pending |
| VLD-070 | 2026-07-28 | Canonical CLI check-config | `env -u PYTHONPATH -u PYTHONHOME uv run lr-ai-exposure --check-config` | exit 0, summary printed | Config + main.py entry point | WO-022 | pending |
| VLD-071 | 2026-07-28 | Focused WO-022 tests | `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_main_integration.py tests/test_cli_modes.py` | 10 passed, 0 failed | main.py + analysis_result.py + tests | WO-022 | pending |
| VLD-072 | 2026-07-28 | Diff check | `git diff --check` | pass (CRLF warnings only) | All WO-022 allowed files | WO-022 | pending |
| VLD-073 | 2026-07-28 | Git scope | `git status --short` | only WO-022 allowed files | WO-022 file scope | WO-022 | pending |
| VLD-074 | 2026-07-28 | 5-image ANALYZE_ONLY integration | `pytest -q tests/test_main_integration.py` | CANONICAL_CLI_EXIT_0, VALIDATED_DECISIONS_5, FULL_DECISION_SCHEMA_WRITTEN, ANALYSIS_EVIDENCE_WRITTEN, APPLY_FUNCTION_NOT_CALLED, NO_XMP_MUTATION | Canonical CLI runtime flow | WO-022 | pending |


### WO-023 (Manual Batch Provider and Evidence Contract)

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-075 | 2026-07-28 | Focused WO-023 tests | `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/test_manual_batch_provider.py tests/test_analysis_artifacts.py` | 21 passed, 0 failed | manual_app batch contract + AnalysisRecord | WO-023 | pending |
| VLD-076 | 2026-07-28 | Full pytest suite | `env -u PYTHONPATH -u PYTHONHOME uv run pytest -q tests/` | 178 passed, 2 skipped (pre-existing) | src/lr_ai_exposure/ + tests/ | WO-023 | pending |
| VLD-077 | 2026-07-28 | 5-entry batch acceptance | `pytest tests/test_manual_batch_provider.py::test_batch_five_decisions_in_manifest_order` | MANIFEST_RESPONSE_ID_SET_RECONCILED, MANUAL_RESPONSES_5, VALIDATED_DECISIONS_5, ANALYSIS_RECORDS_5, ORDER_PRESERVED, PROVIDER_METADATA_PRESERVED | manual_app batch flow | WO-023 | pending |
| VLD-078 | 2026-07-28 | Fail-closed rejection matrix | `pytest tests/test_manual_batch_provider.py` (missing/unknown/duplicate/malformed/missing-id/escape cases) | UNKNOWN_RESPONSES_0, MISSING_RESPONSES_0 enforced by preflight rejection; no partial artifacts | resolve_manual_response_map | WO-023 | pending |
| VLD-079 | 2026-07-28 | Diff check | `git diff --check` | pass (CRLF warnings only) | All WO-023 allowed files | WO-023 | COMMIT: THIS_COMMIT |
| VLD-080 | 2026-07-28 | Git scope | `git status --short` | only WO-023 allowed files | WO-023 file scope | WO-023 | COMMIT: THIS_COMMIT |

### WO-024 (Reproducible CLI Certification) — status: COMPLETED (2026-07-29)

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-081 | 2026-07-29 | Synthetic fixtures | `pytest -q tests/` (fixtures) | 181 passed, 2 skipped | tests/fixtures/ + tests/integration/ | WO-024 | 17a82dd |
| VLD-082 | 2026-07-29 | CLI config smoke | `lr-ai-exposure --check-config` | exit 0, dry_run=true | Config validation | WO-024 | 17a82dd |
| VLD-083 | 2026-07-29 | ANALYZE_ONLY integration | `pytest -q tests/integration/` | 3 passed, 0 failed | ANALYZE_ONLY cannot reach apply; no XMP mutation | WO-024 | 17a82dd |
| VLD-084 | 2026-07-29 | Diff check | `git diff --check` | pass (CRLF warnings only) | All WO-024 allowed files | WO-024 | 17a82dd |
| VLD-085 | 2026-07-29 | Git scope | `git status --short` | only WO-024 allowed files | WO-024 file scope | WO-024 | 17a82dd |
| VLD-086 | 2026-07-29 | Windows CI py312 | GitHub Actions run 30382636338 + 30384086375, job `test-windows (3.12)` | VERIFIED success (both runs) | .github/workflows/ci.yml | WO-024 | 17a82dd, e274c74 |
| VLD-087 | 2026-07-29 | Windows CI py313 | GitHub Actions run 30382636338 + 30384086375, job `test-windows (3.13)` | VERIFIED success (both runs) | .github/workflows/ci.yml | WO-024 | 17a82dd, e274c74 |

WO-024 closure markers `WINDOWS_PY312_CI_PASSED` and `WINDOWS_PY313_CI_PASSED`
verified by inspected GitHub Actions run results (not workflow-file existence).
Both matrix jobs reported conclusion=success on Python 3.12 and 3.13.
Local (non-CI) evidence above re-verified on 2026-07-29.

### WO-025 (Transactional XMP Apply Pilot)

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-088 | 2026-07-29 | Transaction tests | `pytest -q tests/test_apply_transaction.py` | 3 passed | apply_transaction.py | WO-025 | pending |
| VLD-089 | 2026-07-29 | CLI auth tests | `pytest -q tests/test_authorized_apply_cli.py` | 2 passed | main.py 2-key auth | WO-025 | pending |
| VLD-090 | 2026-07-29 | Full pytest suite | `uv run pytest -q tests/` | 185 passed | all tests | WO-025 | pending |
| VLD-091 | 2026-07-29 | Diff check | `git diff --check` | pass (CRLF warnings only) | WO-025 allowed files | WO-025 | pending |
| VLD-092 | 2026-07-29 | Git scope | `git status --short` | clean except allowed files | WO-025 file scope | WO-025 | pending |

### WO-026 (Lightroom Bridge and Metadata Refresh) — pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-093 | 2026-07-29 | Bridge tests | `uv run pytest -q tests/test_lightroom_bridge_contract.py tests/test_metadata_refresh_gate.py` | 6 passed | bridge contract | WO-026 | pending |
| VLD-094 | 2026-07-29 | Full test suite | `uv run pytest -q tests/` | 185 passed | all tests | WO-026 | pending |
| VLD-095 | 2026-07-29 | Diff check | `git diff --check` | pass (trailing whitespace/CRLF only) | WO-026 allowed files | WO-026 | pending |
| VLD-096 | 2026-07-29 | Bridge version | bridge.py | 1.0 enforced | `test_lightroom_bridge_contract.py` | WO-026 | pending |
| VLD-097 | 2026-07-29 | Metadata refresh | `test_metadata_refresh_gate.py` | bypasses failures, applies VERIFIED | Python refresh gate | WO-026 | pending |
| VLD-098 | 2026-07-29 | Plugin safety | `test_lightroom_plugin.py` | LrTasks.execute allowed for CLI | Lua static checks | WO-026 | pending |

### WO-027 (Controlled Batch Expansion - Stage A) — pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-099 | 2026-07-29 | Test suite | `uv run pytest -q tests/` | 185 passed | all tests | WO-027 | pending |
| VLD-100 | 2026-07-29 | Integration test suite | `uv run pytest -q tests/integration/` | 3 passed | integration | WO-027 | pending |
| VLD-101 | 2026-07-29 | Diff check | `git diff --check` | pass (trailing whitespace/CRLF only) | WO-027 allowed files | WO-027 | pending |
| VLD-102 | 2026-07-29 | Git scope | `git status --short` | clean except allowed files | WO-027 file scope | WO-027 | pending |

### WO-027 (Controlled Batch Expansion - Stage B) — pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-103 | 2026-07-29 | Checkpoint/resume test | `uv run pytest -q tests/test_batch_apply.py` | 1 passed | `test_batch_apply.py` | WO-027 | pending |
| VLD-104 | 2026-07-29 | Diff check | `git diff --check` | pass | WO-027 allowed files | WO-027 | pending |

### WO-027 (Controlled Batch Expansion - Stage C) — pending

| Validation ID | Date | Subject | Command | Result | Evidence Scope | Work Order | Commit |
|---|---|---|---|---|---|---|---|
| VLD-105 | 2026-07-29 | Final test suite | `uv run pytest -q tests/` | 186 passed | all tests | WO-027 | pending |
| VLD-106 | 2026-07-29 | Diff check | `git diff --check` | pass | WO-027 allowed files | WO-027 | pending |

## Evidence Scope Definitions

- **Full** — command was run, result is as stated
- **Pending** — validation not yet executed at time of evidence capture
- **Historical** — evidence from prior committed state, not re-run

## Limitations

- No Lightroom runtime integration has been validated.
- Google Vision API is correctly wired but blocked by quota limit.
- No live XMP write has been validated against real Lightroom catalogs.
- All git-scope validation applies to tracked files only.

