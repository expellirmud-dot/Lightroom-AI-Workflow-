# WO-002 — Documentation Governance

STATUS: ACTIVE

## Objective

Establish the documentation authority, index, and closeout governance
for the Lightroom AI Exposure project so that future Work Orders
leave canonical documents consistent with implemented repository truth.

## Scope

This Work Order governs documentation infrastructure only. It does
**not** change any runtime code, configuration values, AI contracts,
or Lightroom integration behavior.

## Files Covered (WO-002 only)

- `AGENTS.md`
- `docs/INDEX.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `Work-Order/WO-002-DOCUMENTATION-GOVERNANCE.md`

## Changes Implemented

### `docs/INDEX.md` (new)

Created the canonical documentation index. Establishes:

- Authority order (Active WO > AGENTS.md > safety > architecture > decisions > tests > user docs)
- Required read set for every coding task
- Maintained documents table with read/update triggers
- Placement rules (narrowest canonical location)
- Lifecycle classifications (ACTIVE, HISTORICAL, SUPERSEDED, DRAFT)
- Closeout checklist

### `AGENTS.md` (updated)

Added the following sections between the existing Final Report Format
and the top of the file (preserving all original content):

1. **Documentation Authority and Index** — requires agents to use
   `docs/INDEX.md` to identify governing documents before implementation.
2. **Documentation Closeout Gate** — every Work Order must review all
   affected canonical documents before closeout.
3. **Required Documentation Outcomes** — UPDATED / REVIEWED_NO_CHANGE /
   NOT_APPLICABLE / BLOCKED.
4. **Required Knowledge Capture** — material decisions, constraints,
   risks, and deferred work must be preserved in canonical documents.
5. **Documentation Stop Conditions** — six explicit stop conditions.
6. **Extended Completion Gate** — documentation reconciliation is now
   part of the completion gate.
7. **Final Report Documentation Section** — five required fields in
   every final report.

### `Work-Order/CURRENT_WORK_ORDER.md`

Updated to point to WO-002 as the active Work Order.

### `Work-Order/WO-002-DOCUMENTATION-GOVERNANCE.md`

This file.

## Documentation Impact Review

| Document | Outcome | Reason |
|----------|---------|--------|
| `AGENTS.md` | UPDATED | Added documentation governance sections |
| `docs/INDEX.md` | CREATED | New canonical index |
| `README.md` | REVIEWED_NO_CHANGE | No user-facing setup or usage changes in this WO |
| `docs/ARCHITECTURE.md` | REVIEWED_NO_CHANGE | Architecture unchanged |
| `docs/XMP_SAFETY.md` | REVIEWED_NO_CHANGE | XMP contract unchanged |
| `docs/AI_JUDGE_CONTRACT.md` | REVIEWED_NO_CHANGE | AI contract unchanged |
| `docs/DECISIONS.md` | REVIEWED_NO_CHANGE | No new architectural decisions |
| `Work-Order/CURRENT_WORK_ORDER.md` | UPDATED | Pointer changed to WO-002 |
| `Work-Order/WO-001-PROJECT-SCAFFOLD.md` | REVIEWED_NO_CHANGE | Historical, not current authority |

## Knowledge Captured

- Documentation governance is now part of the project's execution rules.
- `docs/INDEX.md` is the single source of truth for which documents are authoritative.
- Every future Work Order must include a documentation impact review.
- The authority order (AGENTS.md > safety contracts > architecture > decisions > tests > user docs) is now explicitly recorded.
- Documentation closeout is a hard gate — code complete without docs reconciliation is not WO complete.
- `CURRENT_WORK_ORDER.md` now points to WO-002, which is the template for all future WO closeouts.

## Required Documentation Outcomes

- `AGENTS.md` → UPDATED
- `docs/INDEX.md` → CREATED → ACTIVE
- `README.md` → REVIEWED_NO_CHANGE
- `docs/ARCHITECTURE.md` → REVIEWED_NO_CHANGE
- `docs/XMP_SAFETY.md` → REVIEWED_NO_CHANGE
- `docs/AI_JUDGE_CONTRACT.md` → REVIEWED_NO_CHANGE
- `docs/DECISIONS.md` → REVIEWED_NO_CHANGE
- `Work-Order/CURRENT_WORK_ORDER.md` → UPDATED

## Remaining Risks

- `docs/INDEX.md` is newly created and has no historical predecessor — no superseded documents to track yet.
- FUTURE WORK Orders should follow the WO-002 template for documentation sections and closeout format.
- The `.gitignore` does not explicitly ignore `docs/INDEX.md` backups or temporary draft docs — no action required yet as none exist.

## Stop Condition

NONE — all validations passed, documentation governance is in place.

WORKER_DONE
