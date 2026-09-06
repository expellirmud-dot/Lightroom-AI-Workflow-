# WO-043 — Development History & Documentation Archive

STATUS: COMPLETE_DOCUMENTED
ACTIVATED: 2026-09-06
CLOSED: 2026-09-06

## Trigger

Owner requested one root-level project history document that explains what each Work Order did, plus a cleanup pass that moves clearly obsolete/superseded documentation into one archival location instead of leaving duplicate historical authority mixed with maintained documents.

WO-042 is complete/integrated. WO-041 remains `AWAITING_OWNER_VALIDATION` and will resume as the current live Lightroom gate after this bounded documentation task closes.

## Goal

Create a durable root-level development ledger, make maintained-document authority easier to understand, and archive only clearly historical/unreferenced duplicates without deleting historical evidence or changing implementation/runtime behavior.

## Authorized scope

- create root `DEVELOPMENT_HISTORY.md`;
- create `archive/README.md` and `archive/legacy-docs/`;
- move clearly superseded/unreferenced historical planning/evidence notes into `archive/legacy-docs/`;
- update `docs/INDEX.md`, `README.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/CAPABILITY_MATRIX.md`, `docs/VALIDATION_REGISTER.md`, and `Work-Order/CURRENT_WORK_ORDER.md` as needed to reflect document authority/placement;
- update this Work Order and WO-041 status pointer on closeout;
- documentation/reference/link tests or bounded scripts under `tests/` only if useful.

## Explicit archive candidates

The following files were read and classified as historical duplicates/superseded artifacts, not current authority:

- root `IDEA.md` — initial two-line concept, superseded by mission/architecture/roadmap;
- `archive/legacy-docs/WO-015-EVIDENCE-NOTE.md` through `archive/legacy-docs/WO-019-EVIDENCE-NOTE.md` — historical evidence duplicated by Work Orders/capability/validation registers;
- `archive/legacy-docs/ROADMAP-WO-015-TO-WO-020.md` — explicitly marked `COMPLETED_SUPERSEDED` and points to `docs/ROADMAP.md`;
- `archive/legacy-docs/WO-REMEDIATION-PHASE-A-TO-E.md` — completed historical remediation umbrella, not an active Work Order.

These are moved, not deleted. Canonical `Work-Order/WO-*.md` files remain in `Work-Order/` as the detailed task history.

## Forbidden

- no source/runtime/plugin/config behavior change;
- no deletion of historical Work Orders or evidence;
- no rewriting Git history;
- no moving canonical maintained docs out of `docs/`;
- no changing Mission/architecture/product direction merely to simplify documentation;
- no treating stale header labels in old Work Orders as current project truth;
- no commit/push of runtime/private evidence.

## Required behavior

1. `DEVELOPMENT_HISTORY.md` lives at repository root and is the human-readable chronological ledger of Work Orders and major development phases.
2. It clearly states that current truth still comes from `Work-Order/CURRENT_WORK_ORDER.md`, active/parked Work Orders, `docs/PROJECT_STATUS.md`, `docs/CAPABILITY_MATRIX.md`, `docs/VALIDATION_REGISTER.md`, and Git—not from old Work Order header labels.
3. Every numbered Work Order currently present (including split/duplicate numbering such as the two WO-004 scopes and WO-010.1/010.2) is represented with a concise purpose/outcome.
4. `archive/legacy-docs/` contains only non-authoritative historical material and has an index explaining why each file was archived and where current truth lives.
5. `docs/INDEX.md` documents the new root history file and archive placement rule.
6. README links to `DEVELOPMENT_HISTORY.md` for project history.
7. No broken repository references remain to moved files outside the explicit archive index/history references.
8. On closeout, WO-041 becomes the current Work Order again with status `AWAITING_OWNER_VALIDATION`; CAP-054 remains INTEGRATED.

## Acceptance evidence

- all archive candidates moved successfully and no historical file deleted;
- root history covers all `Work-Order/WO-*.md` numbered Work Orders except the archived remediation umbrella, which is listed separately as historical remediation;
- repository search confirms no stale references to old locations except intentionally documented archive mappings;
- maintained authority docs agree on WO-041 as the next/live gate after WO-043 closes;
- full pytest remains green with documented skips;
- `git diff --check` passes;
- working tree contains no runtime/private artifacts.

## Completion state

Close as `COMPLETE_DOCUMENTED` after the archive/history/reference checks pass. This task may update CAP-002 documentation governance evidence but does not promote Lightroom/runtime capabilities.

## Executed closure evidence

- root `DEVELOPMENT_HISTORY.md` contains every distinct numbered Work Order ID currently in `Work-Order/` (45/45 IDs, including split identifiers);
- 8 classified historical duplicate/superseded files were moved intact to `archive/legacy-docs/`;
- `archive/README.md` maps each archived file to current authority;
- bounded stale-location scan found no remaining non-archive references to the moved paths;
- final full pytest exited 0 with 2 expected skips;
- final `git diff --check` exited 0;
- no source/runtime/plugin/config behavior was changed by WO-043;
- WO-041 is restored as the current `AWAITING_OWNER_VALIDATION` gate.
