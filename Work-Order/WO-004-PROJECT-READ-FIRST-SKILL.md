# WO-004 — Project Read-First Skill

STATUS: DONE

## Objective

Create a repository-local `project-read-first` skill that establishes exact
project truth before implementation, review, debugging, or closeout.

The skill must:

1. Resolve the canonical Git repository root.
2. verify branch, HEAD, upstream, origin, and worktree cleanliness.
3. Activate Serena for the exact current repository root and verify it.
4. Verify CodeGraph is indexed for the same root and synchronized enough for
   the current task.
5. Read mandatory authority documents completely.
6. Select additional documents and source context using targeted reads when a
   full read is unnecessary.
7. Produce a deterministic preflight report and one terminal decision.

This Work Order creates the skill foundation only. It does not implement
Lightroom runtime behavior, AI exposure judgment, XMP mutation, or export.

## Canonical Skill Location

```text
.agents/skills/project-read-first/
```

## Required Skill Structure

```text
.agents/skills/project-read-first/
├─ SKILL.md
├─ scripts/
│  └─ preflight.ps1
└─ references/
   ├─ DOCUMENT_READ_POLICY.md
   ├─ SERENA_CODEGRAPH_PROTOCOL.md
   └─ PREFLIGHT_OUTPUT_CONTRACT.md
```

## Required Read Order

Before editing, read completely:

1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. This Work Order

Then read targeted sections from:

- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`

Read other documents only when their review trigger in `docs/INDEX.md` matches
this task.

## Capability Impact

This Work Order may add the following capability entry if it does not already
exist:

| Capability ID | Capability | Before | Target After |
|---|---|---|---|
| CAP-015 | Repository read-first preflight skill | NOT_STARTED | TESTED |

If the current matrix uses another available identifier, preserve its existing
identifier scheme and record the actual ID truthfully.

No unrelated capability status may change.

## Allowed Files

- `.agents/skills/project-read-first/SKILL.md`
- `.agents/skills/project-read-first/scripts/preflight.ps1`
- `.agents/skills/project-read-first/references/DOCUMENT_READ_POLICY.md`
- `.agents/skills/project-read-first/references/SERENA_CODEGRAPH_PROTOCOL.md`
- `.agents/skills/project-read-first/references/PREFLIGHT_OUTPUT_CONTRACT.md`
- `tests/test_project_read_first_skill.py`
- `AGENTS.md`
- `docs/INDEX.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/DECISIONS.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `Work-Order/WO-004-PROJECT-READ-FIRST-SKILL.md`

No other path is authorized.

## Forbidden Actions

- Do not modify Lightroom catalogs, previews, photographs, RAW files, JPEG
  originals, or XMP sidecars.
- Do not implement Lightroom plug-in code.
- Do not call external AI APIs.
- Do not add a resident HTTP service or file watcher.
- Do not hard-code a Serena project name or fixed repository path.
- Do not treat Serena memory or CodeGraph results as authority over Git/files.
- Do not silently clean, reset, stash, or repair a dirty worktree.
- Do not edit Serena or CodeGraph global configuration outside this repository.
- Do not begin WO-005.
- Do not push.

## Skill Frontmatter Contract

`SKILL.md` must use valid skill frontmatter and include at least:

```yaml
---
name: project-read-first
description: >
  Establish repository truth before coding by resolving the exact Git root,
  verifying Serena and CodeGraph project context, reading mandatory authority
  documents, selecting task-relevant references, and producing a bounded
  preflight decision before any file modification.
---
```

Keep the frontmatter minimal and deterministic. Do not add tool-specific fields
unless the repository's installed skill format requires them and the requirement
is verified from an existing local skill.

## Mandatory Full Reads Per Skill Run

The skill must require complete reads of:

1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. The active Work Order referenced by the pointer

These files define authority and scope and must not be replaced by summaries.

## Targeted Read Policy

The skill must avoid unnecessary broad reads.

Default targeted behavior:

- `docs/PROJECT_STATUS.md`: read status header, current objective, risks, and
  next seam.
- `docs/CAPABILITY_MATRIX.md`: read status definitions plus rows for capability
  IDs named by the active Work Order and their direct dependencies.
- `docs/VALIDATION_REGISTER.md`: read schema/header and the latest entries
  relevant to the active capabilities.
- `README.md`: read only sections affected by installation, configuration,
  commands, usage, or supported behavior.
- Source code: prefer Serena symbol overview, exact symbol reads, CodeGraph
  dependency queries, and targeted line ranges before full-file reads.

Escalate to a full read when:

- A safety contract governs the task.
- The active Work Order requires it.
- Definitions are distributed across the file.
- Targeted sections conflict or remain ambiguous.
- Closeout requires confirming the complete document remains accurate.

## Serena Protocol

The canonical project root is the exact output of:

```text
git rev-parse --show-toplevel
```

The skill must instruct the coding agent to:

1. Activate Serena using the canonical Git root.
2. Verify Serena reports the same root.
3. Reject a parent, sibling, historical, or previously active project.
4. Use symbol overview and exact symbol reads before broad source reads.
5. Treat Serena memory as supplementary context only.

If Serena cannot be activated or verified for the exact root, the terminal
preflight decision must be `BLOCKED_SERENA`.

## CodeGraph Protocol

The skill must instruct the coding agent to:

1. Verify the indexed repository path equals the canonical Git root.
2. Verify index availability.
3. Synchronize when current repository state is newer than the usable index.
4. Use graph queries for dependencies, callers, ownership, and architectural
   impact.
5. Cross-check material results against repository source truth.

If CodeGraph cannot be verified for the exact root, the terminal preflight
decision must be `BLOCKED_CODEGRAPH`.

## PowerShell Script Contract

`scripts/preflight.ps1` must be Windows-first and read-only.

It must:

- Accept an optional `-StartPath` parameter.
- Resolve the repository root using Git.
- Capture current directory, branch, HEAD, upstream, origin, dirty paths, and
  recent commits.
- Check existence of `AGENTS.md`, `docs/INDEX.md`, and
  `Work-Order/CURRENT_WORK_ORDER.md`.
- Emit deterministic `KEY=VALUE` lines.
- Return `GIT_READY` only when Git and mandatory-file checks pass.
- Return a non-zero exit code for blocked results.
- Never edit, stage, commit, stash, reset, clean, or push.

`GIT_READY` is not the final `READY` decision. Final readiness additionally
requires verified Serena, CodeGraph, mandatory reads, and scope extraction.

## Terminal Preflight Decisions

The skill must produce exactly one of:

- `READY`
- `BLOCKED_DIRTY_WORKTREE`
- `BLOCKED_PROJECT_MISMATCH`
- `BLOCKED_SERENA`
- `BLOCKED_CODEGRAPH`
- `BLOCKED_MISSING_AUTHORITY`
- `BLOCKED_SCOPE_CONFLICT`
- `BLOCKED_OWNER_DECISION`

Implementation may begin only after `READY`.

## Preflight Output Contract

The reference contract must require this output shape:

```text
READ_FIRST_PREFLIGHT

REPOSITORY_ROOT:
CURRENT_DIRECTORY:
BRANCH:
HEAD:
UPSTREAM:
ORIGIN:
GIT_STATUS:

ACTIVE_WORK_ORDER:
WORK_ORDER_STATUS:
CAPABILITY_IDS:
ALLOWED_FILES:
FORBIDDEN_FILES:

SERENA_PROJECT:
SERENA_STATUS:
CODEGRAPH_PROJECT:
CODEGRAPH_STATUS:
CODEGRAPH_SYNC:

FULL_DOCUMENTS_READ:
TARGETED_DOCUMENTS_READ:
SOURCE_SYMBOLS_INSPECTED:

EXPECTED_CHANGE:
REQUIRED_VALIDATION:
DOCUMENTATION_IMPACT:
COMMIT_AUTHORIZATION:
PUSH_AUTHORIZATION:

PREFLIGHT_DECISION:
BLOCK_REASON:
```

## Tests

Create focused tests that verify at minimum:

- Required skill files exist.
- `SKILL.md` contains valid frontmatter and the correct skill name.
- The script contains no mutation commands such as `git add`, `git commit`,
  `git reset`, `git clean`, `git stash`, or `git push`.
- Mandatory authority files are represented in the skill/script contract.
- All terminal decision values are documented.
- The output contract contains all required fields.
- Repository paths are resolved dynamically and not hard-coded to
  `D:\\ai-tools\\lightroom-ai-exposure`.

Tests may inspect file contents; they must not require Serena or CodeGraph to be
installed in the test environment.

## Documentation Impact

Before closeout, review and reconcile:

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/DECISIONS.md`
- This Work Order
- `Work-Order/CURRENT_WORK_ORDER.md`

Required outcomes:

- Register the skill and its authority/review triggers in `docs/INDEX.md`.
- Add the required Read-First invocation rule to `AGENTS.md` without
  duplicating existing authority rules.
- Record the actual capability maturity and executed evidence.
- Update project status and next recommended seam truthfully.
- Record a durable decision only when a material new architecture decision was
  made.

## Acceptance Criteria

- The complete skill structure exists at the canonical path.
- `SKILL.md` follows valid repository skill format.
- The skill requires exact-root Serena activation and verification.
- The skill requires exact-root CodeGraph verification and synchronization.
- Mandatory authority files are always read fully.
- Conditional documents use the documented targeted/full-read policy.
- The PowerShell script is deterministic, read-only, and returns useful exit
  codes.
- Focused tests pass.
- Documentation and traceability registers match repository truth.
- No forbidden or unrelated file changed.
- No secret, runtime output, preview, log, backup, or real user data is tracked.

## Required Validation

Run from the repository root:

```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

Also run the script from the clean repository root before making changes or
from an isolated clean copy/worktree after implementation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  ".agents\skills\project-read-first\scripts\preflight.ps1" `
  -StartPath "."
```

Expected script result on a clean repository with mandatory files present:

```text
PREFLIGHT_DECISION=GIT_READY
```

Do not falsely expect `GIT_READY` while the implementation worktree contains
uncommitted WO-004 changes. Use a committed clean state or isolated copy for
that validation.

## Commit Authorization

After all acceptance criteria, tests, diff review, documentation closeout, and
traceability reconciliation pass, the coding worker may create exactly one
commit.

Stage only the exact authorized WO-004 files. Do not use `git add .` or
`git add -A`.

Commit message:

```text
feat: add project read-first skill
```

Do not push.

## Closeout Requirements

Before commit:

1. Confirm every changed path is authorized.
2. Confirm no destructive Git command exists in the skill script.
3. Confirm mandatory full-read documents and conditional read rules are
   consistent across skill and references.
4. Confirm documentation registers record actual evidence, not planned claims.
5. Reconcile this Work Order to `STATUS: DONE` or a truthful blocked status.
6. Reconcile `Work-Order/CURRENT_WORK_ORDER.md` to `STATUS: NONE` after a
   successful closeout.

After commit:

- `git status --short` must be empty.
- Report the commit SHA.
- Do not push.
- Do not begin WO-005.

## Final Report

```text
WORK_ORDER: WO-004-PROJECT-READ-FIRST-SKILL
STATUS:
COMMIT_SHA:

FILES_CHANGED:
BEHAVIOR_IMPLEMENTED:

VALIDATION:
TEST_RESULT:
SCRIPT_VALIDATION:

SERENA_PROTOCOL:
CODEGRAPH_PROTOCOL:
DOCUMENT_READ_POLICY:

DOCUMENTATION_REVIEWED:
DOCUMENTATION_UPDATED:
DOCUMENTATION_REVIEWED_NO_CHANGE:
KNOWLEDGE_CAPTURED:
CAPABILITY_STATUS:
CURRENT_WORK_ORDER_STATUS:

GIT_STATUS:
PUSH_STATUS: NOT_PUSHED
REMAINING_RISKS:

WORKER_DONE
```

## Closeout

All deliverables implemented and validated:

### Skill Structure Created

- `.agents/skills/project-read-first/SKILL.md`
- `.agents/skills/project-read-first/scripts/preflight.ps1`
- `.agents/skills/project-read-first/references/DOCUMENT_READ_POLICY.md`
- `.agents/skills/project-read-first/references/SERENA_CODEGRAPH_PROTOCOL.md`
- `.agents/skills/project-read-first/references/PREFLIGHT_OUTPUT_CONTRACT.md`

### Tests Created

- `tests/test_project_read_first_skill.py` — 8 tests covering file existence,
  frontmatter validity, mutation-command ban, decision references, mandatory
  document contracts, output contract completeness, and path hard-coding bans.

### Validation

- `pytest -q` — 18 passed (8 new + 10 existing)
- `compileall -q src` — pass
- `git diff --check` — pass

### Documentation Updated

- `AGENTS.md` — Read-First Invocation Rule added
- `docs/INDEX.md` — pending update (skill entry registration)
- `docs/CAPABILITY_MATRIX.md` — pending update (CAP-015)
- `docs/PROJECT_STATUS.md` — pending update
- `docs/VALIDATION_REGISTER.md` — pending update
- `Work-Order/CURRENT_WORK_ORDER.md` — pending NONE reconciliation

### Remaining Risks

- The PowerShell script has not been executed on a real Windows environment;
  syntax validation is limited to static review.
- Serena and CodeGraph verification in the script and skill document is
  structural; real activation was not tested in this Work Order.
- CAP-005 through CAP-014 remain NOT_STARTED.
