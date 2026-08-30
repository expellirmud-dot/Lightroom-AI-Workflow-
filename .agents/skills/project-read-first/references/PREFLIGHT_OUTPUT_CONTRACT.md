# Preflight Output Contract

This reference document defines the exact output shape the
project-read-first skill must produce.

## Contract

The skill must produce exactly this shape:

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

PREFLIGHT_REUSE: yes | no
DIRTY_CLASSIFICATION: CLEAN | NON_BLOCKING | BLOCKING | CRITICAL
NON_BLOCKING_EXCLUSIONS:

EXPECTED_CHANGE:
REQUIRED_VALIDATION:
DOCUMENTATION_IMPACT:
COMMIT_AUTHORIZATION:

PREFLIGHT_DECISION: READY | BLOCKED_DIRTY_WORKTREE |
  BLOCKED_PROJECT_MISMATCH | BLOCKED_SERENA | BLOCKED_CODEGRAPH |
  BLOCKED_MISSING_AUTHORITY | BLOCKED_SCOPE_CONFLICT |
  BLOCKED_OWNER_DECISION

BLOCK_REASON:
```

## Field Definitions

| Field | Description |
|---|---|
| `REPOSITORY_ROOT` | Output of `git rev-parse --show-toplevel` |
| `CURRENT_DIRECTORY` | Working directory at skill start |
| `BRANCH` | Active branch name |
| `HEAD` | Full commit SHA of HEAD |
| `UPSTREAM` | Upstream branch reference |
| `ORIGIN` | Origin remote URL |
| `GIT_STATUS` | Output of `git status --short` |
| `ACTIVE_WORK_ORDER` | Path to active Work Order or NONE |
| `WORK_ORDER_STATUS` | STATUS field from the Work Order |
| `CAPABILITY_IDS` | Comma-separated capability IDs from CAPABILITY_MATRIX.md |
| `ALLOWED_FILES` | Count of files in the Work Order Allowed Files list |
| `FORBIDDEN_FILES` | Count of paths in the Work Order Forbidden Files/Actions list |
| `SERENA_PROJECT` | Serena project name or path used |
| `SERENA_STATUS` | `active_verified` or `not_verified` |
| `CODEGRAPH_PROJECT` | CodeGraph indexed path |
| `CODEGRAPH_STATUS` | `index_available` or `not_available` |
| `CODEGRAPH_SYNC` | `yes` (index current) or `no` (stale) |
| `FULL_DOCUMENTS_READ` | List of files fully read |
| `TARGETED_DOCUMENTS_READ` | List of files read with targeted sections |
| `SOURCE_SYMBOLS_INSPECTED` | List of symbols inspected via Serena/CodeGraph |
| `PREFLIGHT_REUSE` | Whether a completed same-thread full preflight was reused |
| `DIRTY_CLASSIFICATION` | Material-risk classification of current Git dirty state |
| `NON_BLOCKING_EXCLUSIONS` | Explicit owner/local paths preserved outside task scope |
| `EXPECTED_CHANGE` | Brief description of what the task will do |
| `REQUIRED_VALIDATION` | Validation commands from Work Order |
| `DOCUMENTATION_IMPACT` | `yes` or `no`, list of docs affected |
| `COMMIT_AUTHORIZATION` | `yes` if Work Order authorizes commit, `no` |
| `PREFLIGHT_DECISION` | One of the 8 decision values |
| `BLOCK_REASON` | Empty if READY, otherwise the exact blocking condition |

## Decision Value Reference

| Decision | Meaning |
|---|---|
| `READY` | Required checks passed; explicitly excluded NON_BLOCKING dirty state is permitted |
| `BLOCKED_DIRTY_WORKTREE` | Dirty state is BLOCKING or CRITICAL |
| `BLOCKED_PROJECT_MISMATCH` | Serena/CodeGraph project does not match Git root |
| `BLOCKED_SERENA` | Serena cannot be activated or verified |
| `BLOCKED_CODEGRAPH` | CodeGraph cannot be verified |
| `BLOCKED_MISSING_AUTHORITY` | Mandatory authority document is missing |
| `BLOCKED_SCOPE_CONFLICT` | Active Work Order scope is ambiguous |
| `BLOCKED_OWNER_DECISION` | Action requires owner authorization |
