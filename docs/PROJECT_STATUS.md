# Project Status

LAST_UPDATED: 2026-08-31
PROJECT_PHASE: MVP_CLOSURE_LIVE_CERTIFICATION
CURRENT_WORK_ORDER: Work-Order/WO-039-CATALOG-APPLY-COMMIT-BARRIER.md
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-038-CONTACT-SHEET-PACKAGE-PIPELINE.md
CURRENT_BRANCH: main; Git is authority for moving HEAD

## Current truth

The canonical iterative workflow is implemented and CI-certified through
WO-039. It is no longer a WO-029-only prepared-folder prototype.

```text
Diagnose Current Folder (optional/advisory)
→ Prepare AI Package
→ PACKAGE_READY
→ external AI or deterministic test decision producer
→ Import / Apply AI Results
→ guarded Catalog Exposure2012 apply
→ bounded post-commit Lightroom verification
→ SESSION_COMPLETE or RERENDER_REQUIRED
→ Prepare Next AI Package after rerender
```

The Lightroom plug-in is short-lived and owns explicit Lightroom-side commands.
Python owns read-only preview-cache extraction, immutable package/session data,
decision validation, convergence/safety planning and render freshness. External
AI has decision-only authority. The canonical iterative route does not require
XMP Save/Read Metadata synchronization.

## Evidence already established

- Real Lightroom identity/cache Analyze Only was proven historically.
- Whole-folder/session/package implementation and canonical command separation
  are covered by automated/integration evidence.
- WO-037 Windows certification passed on Python 3.12 and 3.13.
- WO-038 contact-sheet package creation/integrity passed focused and full
  automated validation.
- A representative live session reached a 324-image decision/apply stage.
- Lightroom actually held the 21 requested absolute `Exposure2012` target
  values after apply.

The last point exposed a verification defect rather than a failed mutation:
verification occurred too early inside Lightroom write access, so the old code
observed stale values and incorrectly converted technical verification failures
to photographic REVIEW.

## Current gate — WO-039

WO-039 moves verification outside the write callback, uses bounded post-commit
polling, makes retries absolute-target/idempotent, keeps technical failures out
of photographic REVIEW, and repairs only the affected legacy technical state.
GitHub Actions run #91 passed on Windows/Python 3.12 and 3.13.

Remaining owner-operated acceptance:

```text
re-run Import / Apply AI Results
→ recognize 21 existing targets without a second delta
→ PASS 303 / REVIEW 0
→ RERENDER_REQUIRED
→ allow Lightroom to rerender
→ Prepare Next AI Package
→ prove a fresh generation
```

Do not claim the post-commit barrier or complete iterative loop
`LIVE_VERIFIED` until this bounded recheck succeeds.

## Reconciled legacy conflicts

Canonical project instructions/safety/AI contracts now distinguish the WO-037+
Catalog route from legacy WO-029 XMP behavior and align the visual instruction
bundle with the generated current schema (`action`, `scene_group_id`,
`is_reference`). Relevance/blur/focus/culling instructions are dormant for the
current exposure-only small-preview task.

The optional WO-031 diagnostic implementation still contains legacy
XMP/metadata-sync aggregate readiness semantics that can overstate a
`SAFETY_BLOCKED` result for the current Catalog architecture. Treat those
legacy-only codes as **non-blocking diagnostic debt** during MVP closure unless
they actually block Gate A/B. Do not activate a separate Work Order solely from
that stale aggregate label.

## Phase policy

This project is currently in **MVP closure/live certification**, not general
feature expansion.

Until WO-039 and the next-render proof close:

- do not activate a new Work Order for a defect that belongs to the current
  acceptance gate;
- reconcile stale project instructions/documents as part of WO-039 closeout;
- keep AI model/provider quality, broader image triage, UX expansion, packaging
  and optional provider automation in `docs/ROADMAP.md` backlog;
- create a new Work Order only for a genuinely new capability/boundary after the
  Controller identifies the roadmap gate it advances.

## Current risks / unknowns

- WO-039 fixed verification has CI evidence but still needs Lightroom-hosted
  recheck on the affected live session.
- The next-pass render freshness barrier still needs representative Lightroom
  proof after the corrected apply confirmation.
- Optional WO-031 aggregate diagnostic readiness still carries legacy XMP sync
  assumptions; current canonical Prepare/Apply does not.
- AI photographic quality/calibration remains intentionally deferred and is not
  a blocker for technical MVP closure.
