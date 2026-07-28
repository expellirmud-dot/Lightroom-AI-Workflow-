# WO-003 — Project Traceability Registers

STATUS: ACTIVE

## Objective

Create the canonical project-level traceability system so future agents and
maintainers can determine, without relying on chat history:

- What major capabilities the project contains
- What has not started, is planned, implemented, tested, integrated, or
  verified with real Lightroom data
- Which Work Order and commit changed each capability
- What validation evidence exists and what that evidence actually proves
- What gate remains before a capability can be considered usable in practice
- What the current project phase, risks, and next recommended bounded seam are

This Work Order is documentation-governance only. It does not authorize
Lightroom integration, AI API calls, XMP writes, production code changes, or
runtime execution against real user data.

## Required Read Order

1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. `Work-Order/WO-003-PROJECT-TRACEABILITY-REGISTERS.md`
5. `README.md`
6. `docs/ARCHITECTURE.md`
7. `docs/XMP_SAFETY.md`
8. `docs/AI_JUDGE_CONTRACT.md`
9. `docs/DECISIONS.md`
10. `Work-Order/WO-001-PROJECT-SCAFFOLD.md`
11. `Work-Order/WO-002-DOCUMENTATION-GOVERNANCE.md`

## Scope

### Allowed Files

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `Work-Order/WO-003-PROJECT-TRACEABILITY-REGISTERS.md`

### Forbidden Files and Actions

- Do not change Python source files.
- Do not change tests.
- Do not change `README.md`, `docs/ARCHITECTURE.md`,
  `docs/XMP_SAFETY.md`, `docs/AI_JUDGE_CONTRACT.md`, or
  `docs/DECISIONS.md` unless a direct contradiction prevents truthful
  completion; if so, stop and report instead of widening scope.
- Do not access or modify Lightroom Catalog files, `.lrdata`, RAW files,
  photographs, previews, or XMP sidecars.
- Do not call external AI services.
- Do not install dependencies.
- Do not implement code or later Work Orders.
- Do not push.
- Do not continue to WO-004.

## Canonical Traceability Chain

The repository must support this traceability chain:

```text
Project Objective
→ Capability
→ Work Order
→ Changed Files
→ Validation Evidence
→ Commit
→ Current Capability Status
→ Next Required Gate
```

A completed Work Order alone is not evidence that a capability is ready for
real use.

## Required Status Model

`docs/CAPABILITY_MATRIX.md` must define and use these statuses:

| Status | Meaning |
|---|---|
| `NOT_STARTED` | No authorized implementation exists |
| `PLANNED` | Scope is defined but implementation has not started |
| `IMPLEMENTED` | Code or documentation exists but required validation is incomplete |
| `TESTED` | Focused automated or bounded validation passed |
| `INTEGRATED` | Cross-component workflow validation passed |
| `LIVE_VERIFIED` | Verified with representative Lightroom Classic and real project data |
| `BLOCKED` | Work cannot safely continue until a stated condition is resolved |
| `DEFERRED` | Explicitly postponed outside the active delivery phase |
| `RETIRED` | No longer part of the active system |

Rules:

- Code existence supports at most `IMPLEMENTED`.
- Focused automated tests support at most `TESTED`.
- Successful cross-component validation supports `INTEGRATED`.
- Representative use with Lightroom Classic and real files is required for
  `LIVE_VERIFIED`.
- Worker reports alone do not change capability status.
- Planned work must never be recorded as completed work.

## Required Deliverables

### 1. `docs/PROJECT_STATUS.md`

Create a concise current-state summary containing at least:

- `LAST_UPDATED`
- `PROJECT_PHASE`
- `CURRENT_WORK_ORDER`
- `LATEST_COMPLETED_WORK_ORDER`
- `LATEST_COMMIT`
- Current project objective
- Overall status table
- Current known risks
- Next recommended bounded seam

Initial repository truth must recognize:

- WO-001 project scaffold completed in commit `a7228cc`
- WO-002 documentation governance completed in commit `192a5e6`
- No Lightroom integration, Vision AI execution, XMP write, Lightroom
  read-back, or real-photo pilot has been completed

Do not claim statuses beyond available evidence.

### 2. `docs/CAPABILITY_MATRIX.md`

Create the canonical capability register.

It must contain at least these initial capabilities:

| ID | Capability |
|---|---|
| `CAP-001` | Project configuration foundation |
| `CAP-002` | Documentation governance |
| `CAP-003` | Job directory creation |
| `CAP-004` | Ordered image manifest |
| `CAP-005` | Lightroom selected-photo retrieval |
| `CAP-006` | Lightroom rendered-preview export |
| `CAP-007` | Vision AI batch submission |
| `CAP-008` | AI decision schema validation |
| `CAP-009` | Exposure delta limiting |
| `CAP-010` | XMP backup and restore safety |
| `CAP-011` | `crs:Exposure2012` update |
| `CAP-012` | Lightroom metadata read-back |
| `CAP-013` | Reject suggestions |
| `CAP-014` | Automatic export |

Each capability row must include:

- Capability ID
- Capability name
- Current status
- Work Order
- Commit
- Evidence
- Next gate

Initial status must be conservative and evidence-based. `CAP-001` may be
recorded as `TESTED` based on WO-001 validation. `CAP-002` may be recorded as
`TESTED` based on WO-002 documentation and clean Git validation. All other
capabilities must remain `NOT_STARTED`. `CAP-014` is `DEFERRED`.

### 3. `docs/VALIDATION_REGISTER.md`

Create the canonical executed-evidence register.

Each row must contain:

- Validation ID
- Date
- Subject
- Validation command or method
- Result
- Evidence scope
- Work Order
- Commit

Seed only evidence supported by repository history and completed Work Orders.
At minimum record the WO-001 evidence:

- `pytest -q` — 10 passed
- `python -m compileall -q src` — pass
- `python -m lr_ai_exposure.main --check-config` — exit 0
- `git diff --check` — pass

Record WO-002 only as documentation/Git-scope validation that was actually
reported. Do not invent unexecuted commands, dates, or test counts.

The register must distinguish between:

- Automated test evidence
- Static or syntax validation
- Git/diff scope validation
- Integration validation
- Live Lightroom validation

### 4. Update `AGENTS.md`

Add a `Project Traceability` section requiring every material Work Order to:

Before implementation:

- Identify affected capability IDs
- Record current status
- Declare target status
- Define the evidence required for the target status

Before closeout:

- Reconcile target versus actual status
- Update `docs/CAPABILITY_MATRIX.md`
- Add new executed evidence to `docs/VALIDATION_REGISTER.md`
- Update `docs/PROJECT_STATUS.md`
- Record incomplete or failed gates truthfully
- Link the Work Order and commit when available

Also add explicit status-truth rules from this Work Order.

### 5. Update `docs/INDEX.md`

Register these new canonical documents:

- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`

For each, define purpose, read trigger, and update trigger.

Update the documentation placement rules and closeout checklist so project
status, capability maturity, and executed evidence are reconciled before every
future Work Order closes.

### 6. Reconcile Work Order State

At closeout:

- Update this Work Order from `STATUS: ACTIVE` to `STATUS: DONE` only after all
  acceptance criteria and validation pass.
- Add a truthful closeout section containing documentation outcomes,
  validation evidence, committed files, capability impact, remaining risks,
  and commit placeholder if the SHA is not yet available before commit.
- Update `Work-Order/CURRENT_WORK_ORDER.md` to a truthful terminal state:

```text
STATUS: NONE
WORK_ORDER: NONE
LATEST_COMPLETED_WORK_ORDER: `Work-Order/WO-003-PROJECT-TRACEABILITY-REGISTERS.md`
```

It must not continue pointing at a completed Work Order.

## Capability Impact

This Work Order is authorized to create or update traceability for all listed
capabilities but must not claim implementation progress beyond existing
repository evidence.

| Capability | Before | Target After |
|---|---|---|
| Project traceability governance | NOT_STARTED | TESTED |
| Project status reporting | NOT_STARTED | TESTED |
| Capability maturity register | NOT_STARTED | TESTED |
| Validation evidence register | NOT_STARTED | TESTED |

`TESTED` here means documentation structure, internal consistency, and Git
scope validation have passed. It does not mean Lightroom runtime integration
or live use has occurred.

## Acceptance Criteria

- `docs/PROJECT_STATUS.md` exists and truthfully summarizes repository state.
- `docs/CAPABILITY_MATRIX.md` exists with the required status definitions and
  initial capability register.
- `docs/VALIDATION_REGISTER.md` exists with only executed evidence.
- `AGENTS.md` requires capability and validation reconciliation for future
  Work Orders.
- `docs/INDEX.md` lists and governs all three new canonical documents.
- WO-001 and WO-002 evidence is linked conservatively and accurately.
- No capability is promoted beyond its evidence level.
- No code, test, runtime, Lightroom, image, or XMP file is changed.
- Documentation contains no secrets or user photo data.
- `Work-Order/CURRENT_WORK_ORDER.md` is reconciled to `STATUS: NONE` after
  completion.
- Final Git scope contains only allowed files.

## Validation

Run and record:

```powershell
git status --short
git diff --check
git diff --name-only
git diff --stat
```

Perform targeted content checks proving:

- All required status names exist in `docs/CAPABILITY_MATRIX.md`.
- Every initial capability ID from `CAP-001` through `CAP-014` appears exactly
  once.
- The three new documents appear in `docs/INDEX.md`.
- `AGENTS.md` contains the traceability and status-truth requirements.
- `docs/PROJECT_STATUS.md` does not claim Lightroom or XMP implementation.
- `docs/VALIDATION_REGISTER.md` contains no invented live validation.
- `CURRENT_WORK_ORDER.md` is terminal and does not point to WO-002 or active
  WO-003 after closeout.

Use a read-only one-shot validation command. Do not add a
new permanent validation script in this Work Order.

## Commit Authorization

After all acceptance criteria and validation pass, the coding worker may
create exactly one commit for WO-003.

Commit rules:

- Stage only the exact allowed files.
- Do not use `git add .` or `git add -A`.
- Commit message:

```text
docs: add project traceability registers
```

- Do not push.
- Confirm `git status --short` is empty after commit.
- Stop after the commit.

## Traceability and Closeout

Required outcomes:

- `AGENTS.md`: `UPDATED`
- `docs/INDEX.md`: `UPDATED`
- `docs/PROJECT_STATUS.md`: `UPDATED`
- `docs/CAPABILITY_MATRIX.md`: `UPDATED`
- `docs/VALIDATION_REGISTER.md`: `UPDATED`
- `Work-Order/CURRENT_WORK_ORDER.md`: `UPDATED`
- `Work-Order/WO-003-PROJECT-TRACEABILITY-REGISTERS.md`: `UPDATED`

Knowledge captured must include:

- Capability maturity model
- Traceability chain
- Existing verified repository baseline
- Difference between tested, integrated, and live-verified status
- Required future closeout reconciliation
- Linking of committed Work Orders to capabilities they delivered

## Stop Conditions

Stop and report without broad cleanup when:

- Existing repository evidence conflicts with the baseline stated here.
- WO-001 or WO-002 commits cannot be found.
- Any unexpected dirty or untracked file exists before editing.
- An allowed file contains conflicting authority that cannot be reconciled
  within this Work Order.
- A capability status cannot be assigned without guessing.
- Validation would require modifying code or using real Lightroom data.
- The final diff contains a file outside the allowed list.

## Final Report

Report exactly:

```text
WORK_ORDER: WO-003-PROJECT-TRACEABILITY-REGISTERS
STATUS: DONE | BLOCKED
COMMIT_SHA: <sha or NONE>
FILES_COMMITTED:
- ...
CAPABILITY_IMPACT:
CAP-001 through CAP-014 status table
VALIDATION:
DOCUMENTATION_REVIEWED:
DOCUMENTATION_UPDATED:
DOCUMENTATION_REVIEWED_NO_CHANGE:
KNOWLEDGE_CAPTURED:
CURRENT_WORK_ORDER_STATUS:
GIT_STATUS:
REMAINING_RISKS:
WORKER_DONE

## Closeout

- All required traceability documents created.
- AGENTS.md Project Traceability section added.
- docs/INDEX.md updated with new canonical documents.
- docs/PROJECT_STATUS.md, docs/CAPABILITY_MATRIX.md, and docs/VALIDATION_REGISTER.md created.
- Work-Order/CURRENT_WORK_ORDER.md reconciled to STATUS: NONE.
- No code, test, or runtime file was changed.
```
