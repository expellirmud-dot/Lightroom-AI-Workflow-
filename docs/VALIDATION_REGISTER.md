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
| VLD-051 | 2026-07-28 | pytest WO-016 | pytest -q tests/test_cache_extractor.py | 2 passed, 0 failed | src/lr_ai_exposure/cache_extractor.py + tests/ | WO-016 | pending |
| VLD-052 | 2026-07-28 | Live Batch 10 | python scratch/test_batch_extract.py | 10/10 FOUND, JPEGs saved | Real Lightroom cache DBs | WO-016 | pending |

## Evidence Scope Definitions

- **Full** — command was run, result is as stated
- **Pending** — validation not yet executed at time of evidence capture
- **Historical** — evidence from prior committed state, not re-run

## Limitations

- No Lightroom runtime integration has been validated.
- No Vision API integration has been validated.
- No live XMP write has been validated against real Lightroom catalogs.
- All git-scope validation applies to tracked files only.
