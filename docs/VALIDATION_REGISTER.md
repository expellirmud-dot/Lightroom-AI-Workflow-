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
| VLD-028 | 2026-07-28 | Git scope | `git status --short` | clean after commit | Only allowed files changed | WO-006 | pending |

## Evidence Scope Definitions

- **Full** — command was run, result is as stated
- **Pending** — validation not yet executed at time of evidence capture
- **Historical** — evidence from prior committed state, not re-run

## Limitations

- No Lightroom runtime integration has been validated.
- No Vision API integration has been validated.
- No live XMP write has been validated against real Lightroom catalogs.
- All git-scope validation applies to tracked files only.
