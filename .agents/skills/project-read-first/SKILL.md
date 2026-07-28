---
name: project-read-first
description: >
  Establish repository truth before coding by resolving the exact Git
  root, verifying Serena and CodeGraph project context, reading mandatory
  authority documents, selecting task-relevant references, and producing
  a bounded preflight decision before any file modification.
---

# Project Read-First Skill

Use this skill at the start of every coding task to establish exact
project truth before reading implementation files or making changes.

## 1. Resolve Git Repository Root

Run:

```powershell
git rev-parse --show-toplevel
```

The repository root is the canonical project root for all subsequent
steps. Do not assume or hard-code the root from a previous session.

## 2. Verify Repository State

From the canonical Git root, capture:

- Current directory (`pwd`)
- Active branch (`git branch --show-current`)
- HEAD commit (`git rev-parse HEAD`)
- Upstream branch (`git rev-parse --abbrev-ref HEAD@{upstream}` if
  one exists)
- Origin URL (`git remote get-url origin`)
- Git status (`git status --short`)

If the working tree is dirty with untracked or modified files that are
not part of the active Work Order's allowed changes, stop and report
`BLOCKED_DIRTY_WORKTREE`.

## 3. Activate Serena for the Exact Repository Root

Activate Serena using the canonical Git root:

```python
mcp__serena__activate_project(project="D:\\ai-tools\\lightroom-ai-exposure")
```

Then verify Serena is active:

```python
config = mcp__serena__get_current_config()
```

Confirm the active project path matches the canonical Git root from
step 1. If it does not match, use the correct project name from
`config.projects` or pass the absolute root path to `activate_project`.

Reject a parent, sibling, historical, or previously active project.

## 4. Verify CodeGraph Is Indexed for the Same Root

Run CodeGraph diagnostics or an introspection query to confirm the
indexed path equals the canonical Git root and that the index is
recent enough for the current task.

If CodeGraph cannot be verified for the exact root, the terminal
preflight decision must be `BLOCKED_CODEGRAPH`.

## 5. Read Mandatory Authority Documents (Full Read)

Read these documents completely before any other task work:

1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. The active Work Order referenced by `CURRENT_WORK_ORDER.md`

These files define authority and scope. Do not replace them with
summaries.

## 6. Read Targeted Documents (Conditional)

Based on the active Work Order's scope, read additional documents
only as needed. Prefer targeted section reads over full-file reads.

Default targeted behavior:

- `docs/PROJECT_STATUS.md` — read status header, current objective,
  risks, and next seam.
- `docs/CAPABILITY_MATRIX.md` — read status definitions plus rows for
  capability IDs named by the active Work Order and their direct
  dependencies.
- `docs/VALIDATION_REGISTER.md` — read schema/header and the latest
  entries relevant to the active capabilities.
- `README.md` — read only sections affected by installation,
  configuration, commands, usage, or supported behavior.
- Source code — prefer Serena symbol overview, exact symbol reads,
  CodeGraph dependency queries, and targeted line ranges before full
  file reads.

Escalate to a full read when:

- A safety contract governs the task.
- The active Work Order requires it.
- Definitions are distributed across the file.
- Targeted sections conflict or remain ambiguous.
- Closeout requires confirming the complete document remains accurate.

## 7. Produce Preflight Report

Output a deterministic preflight report in this exact shape:

```text
READ_FIRST_PREFLIGHT

REPOSITORY_ROOT: <absolute path from git rev-parse --show-toplevel>
CURRENT_DIRECTORY: <pwd>
BRANCH: <git branch --show-current>
HEAD: <git rev-parse HEAD>
UPSTREAM: <abbreviated upstream branch>
ORIGIN: <git remote get-url origin>
GIT_STATUS: <output of git status --short>

ACTIVE_WORK_ORDER: <path or NONE>
WORK_ORDER_STATUS: <status from Work Order file or NONE>
CAPABILITY_IDS: <comma-separated capability IDs from matrix>
ALLOWED_FILES: <count of allowed files listed in Work Order>
FORBIDDEN_FILES: <count of forbidden paths listed in Work Order>

SERENA_PROJECT: <project name or path used>
SERENA_STATUS: <active verified>
CODEGRAPH_PROJECT: <project name or path verified>
CODEGRAPH_STATUS: <index verified>
CODEGRAPH_SYNC: <yes/no>

FULL_DOCUMENTS_READ: <comma-separated list of files fully read>
TARGETED_DOCUMENTS_READ: <comma-separated list of targeted reads>
SOURCE_SYMBOLS_INSPECTED: <comma-separated list of symbols inspected>

EXPECTED_CHANGE: <brief description of what the task will do>
REQUIRED_VALIDATION: <commands from Work Order validation section>
DOCUMENTATION_IMPACT: <yes/no and which docs affected>
COMMIT_AUTHORIZATION: <yes if Work Order explicitly authorizes, no otherwise>

PREFLIGHT_DECISION: READY | BLOCKED_DIRTY_WORKTREE |
  BLOCKED_PROJECT_MISMATCH | BLOCKED_SERENA | BLOCKED_CODEGRAPH |
  BLOCKED_MISSING_AUTHORITY | BLOCKED_SCOPE_CONFLICT |
  BLOCKED_OWNER_DECISION

BLOCK_REASON: <empty if READY, otherwise exact reason>
```

## 8. Terminal Preflight Decisions

The skill must produce exactly one of:

| Decision | Meaning |
|---|---|
| `READY` | All checks passed; implementation may begin |
| `BLOCKED_DIRTY_WORKTREE` | Unexpected dirty or untracked files exist |
| `BLOCKED_PROJECT_MISMATCH` | Serena or CodeGraph project does not match Git root |
| `BLOCKED_SERENA` | Serena cannot be activated or verified for the exact root |
| `BLOCKED_CODEGRAPH` | CodeGraph cannot be verified for the exact root |
| `BLOCKED_MISSING_AUTHORITY` | Mandatory authority document is missing |
| `BLOCKED_SCOPE_CONFLICT` | Active Work Order scope is ambiguous |
| `BLOCKED_OWNER_DECISION` | Action requires owner authority |

Implementation may begin only after `READY`.

## Safety Rules

- Do not modify the repository root or Git state during preflight.
- Do not edit files during preflight; only read.
- Do not access Lightroom catalogs, preview caches, photographs, RAW
  files, or XMP files during preflight (unless the active Work Order
  explicitly authorizes XMP read-back).
- Do not call external AI services during preflight.
- Do not install dependencies during preflight.
- Do not commit or push during preflight.

## Read-First Invocation Rule

Every coding task must invoke this skill before implementation begins.
The active Work Order's Required Read Order section defines the
mandatory read set; this skill defines the verification that those
reads completed correctly.