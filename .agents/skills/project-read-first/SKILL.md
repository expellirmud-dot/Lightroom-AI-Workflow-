---
name: project-read-first
description: >
  Establish or reuse repository truth before work, classify dirty state by
  material risk, and use delta preflight while HEAD, authority, relevant files,
  and task context remain unchanged.
---

# Project Read-First Skill

Use this skill at the start of every task that may change repository files.
Establish exact project truth once, then reuse that same-thread preflight with
bounded delta checks while its fingerprints remain unchanged.

## 0. Reuse a Same-Thread Preflight When Valid

Reuse a completed preflight when all of these remain true:

- conversation context still contains the full preflight and required reads;
- Git HEAD is unchanged;
- `Work-Order/CURRENT_WORK_ORDER.md` points to the same active Work Order;
- relevant authority/task files have unchanged status and SHA-256;
- task scope has not materially changed beyond the active Work Order;

For reuse, run only delta preflight: Git status, HEAD, active Work Order
pointer, and relevant-file status/hash. Repeat full reads only when one of these fingerprints changed,
context is unavailable, or repository policy explicitly requires it.

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

Classify every dirty path before choosing a terminal decision:

- `NON_BLOCKING` — an explicitly identified pre-existing owner/local change is
  unrelated to task files and proof and can remain untouched and excluded.
  Continue with `READY` and record the exclusion.
- `BLOCKING` — the dirty path overlaps task scope, authority, validation input,
  expected output, or result attribution. Stop with
  `BLOCKED_DIRTY_WORKTREE`.
- `CRITICAL` — the dirty state creates a secrets, destructive-action,
  authorization, safety-evidence, catalog/cache/photo/XMP, or preservation
  risk. Stop with `BLOCKED_DIRTY_WORKTREE` and identify the critical reason.

Git status alone is not a stop condition. Never edit, restore, stash, stage,
commit, or discard a pre-existing owner/local change without explicit owner
authority.

## 3. Serena Is On Demand

Serena = `ON_DEMAND`. Invoke it only for a concrete semantic symbol, source,
or navigation question where it materially improves correctness or efficiency.
Documentation-only work and ordinary bounded implementation do not require it.
When unused, report `SERENA_STATUS: NOT_REQUIRED`.

If the task genuinely requires Serena, activate it using the canonical Git root:

```python
mcp__serena__activate_project(project="<canonical-git-root>")
```

Do not repeat `initial_instructions`, `activate_project`, or
`get_current_config` when project identity is already established. Read current
configuration only when active-project ambiguity materially affects the task.

## 4. CodeGraph Is On Demand

CodeGraph = `ON_DEMAND`. Invoke it only for a concrete dependency,
caller/callee, or impact question. Use narrow queries with bounded results and
normally limit exploration to three to five relevant files. Do not use it to
read ordinary source. When unused, report `CODEGRAPH_STATUS: NOT_REQUIRED`.

`BLOCKED_SERENA` or `BLOCKED_CODEGRAPH` is conditional: the concrete task must
genuinely require the capability, no smaller authoritative method may answer
the question safely, and continuing must materially risk correctness.

## 5. Read Mandatory Authority Documents (Full Read)

Read these documents completely before the first task step, or reuse their
completed same-thread reads under section 0:

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
- Source code — use the smallest sufficient tool: targeted search, bounded
  line reads, ordinary symbol lookup when useful, Serena for material semantic
  navigation, then CodeGraph for material dependency reasoning.

Escalate to a full read when:

- A safety contract governs the task.
- The active Work Order requires it.
- Definitions are distributed across the file.
- Targeted sections conflict or remain ambiguous.
- Closeout requires confirming the complete document remains accurate.

## 6.1 Retrieval Continuity and Anti-Duplication

Never retrieve the same unchanged source body through multiple mechanisms
without a concrete reason. In particular, do not follow a CodeGraph source
dump with a Serena body read and a file read, or a Serena body read with a
full-file read, when the first result already answered the question.

Reread only when the file changed, prior output was incomplete, or a new
concrete question requires a different range or symbol. Once sufficient source
evidence is available, stop retrieval and implement. Same-thread work continues
with delta preflight only when material repository truth changes.

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

SERENA_PROJECT: <canonical root when checked, otherwise NOT_REQUIRED>
SERENA_STATUS: NOT_REQUIRED | READY | AVAILABLE | REQUIRED_BUT_UNAVAILABLE
CODEGRAPH_PROJECT: <indexed root when checked, otherwise NOT_REQUIRED>
CODEGRAPH_STATUS: NOT_REQUIRED | READY | AVAILABLE | REQUIRED_BUT_UNAVAILABLE
CODEGRAPH_SYNC: NOT_REQUIRED | yes | no

FULL_DOCUMENTS_READ: <comma-separated list of files fully read or reused>
TARGETED_DOCUMENTS_READ: <comma-separated list of targeted reads>
SOURCE_SYMBOLS_INSPECTED: <comma-separated list of symbols inspected>

PREFLIGHT_REUSE: yes/no
DIRTY_CLASSIFICATION: CLEAN | NON_BLOCKING | BLOCKING | CRITICAL
NON_BLOCKING_EXCLUSIONS: <paths or NONE>

EXPECTED_CHANGE: <brief description of what the task will do>
REQUIRED_VALIDATION: <commands from Work Order validation section>
DOCUMENTATION_IMPACT: <yes/no and which docs affected>
COMMIT_AUTHORIZATION: <yes if Work Order explicitly authorizes, no otherwise>

PREFLIGHT_DECISION: READY | BLOCKED_DIRTY_WORKTREE |
  BLOCKED_MISSING_AUTHORITY | BLOCKED_SCOPE_CONFLICT |
  BLOCKED_OWNER_DECISION

BLOCK_REASON: <empty if READY, otherwise exact reason>
```

## 8. Terminal Preflight Decisions

The skill must produce exactly one of:

| Decision | Meaning |
|---|---|
| `READY` | Required checks passed; work may begin, including explicitly excluded non-blocking owner changes |
| `BLOCKED_DIRTY_WORKTREE` | Dirty state is classified BLOCKING or CRITICAL |
| `BLOCKED_MISSING_AUTHORITY` | Mandatory authority document is missing |
| `BLOCKED_SCOPE_CONFLICT` | Active Work Order scope is ambiguous |
| `BLOCKED_OWNER_DECISION` | Action requires owner authority |

Implementation may begin only after `READY`. `NON_BLOCKING` dirty state is
compatible with `READY` only when its paths and preservation rules are explicit.

## Safety Rules

- Do not modify repository files or Git state during preflight.
- Do not edit files during preflight; only read.
- Do not access Lightroom catalogs, preview caches, photographs, RAW
  files, or XMP files during preflight (unless the active Work Order
  explicitly authorizes XMP read-back).
- Do not call external AI services during preflight.
- Do not install dependencies during preflight.
- Do not commit or push during preflight.

## Read-First Invocation Rule

Every repository-changing task must invoke this skill before implementation
begins. A valid same-thread invocation may be reused through delta preflight;
invocation does not imply repeated full reads. The active Work Order defines
the required read set and this skill verifies either completed reads or their
valid reuse.
