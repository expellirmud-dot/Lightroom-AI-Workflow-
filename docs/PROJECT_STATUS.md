# Project Status

LAST_UPDATED: 2026-08-31
PROJECT_PHASE: TECHNICAL_MVP_COMPLETE
CURRENT_WORK_ORDER: NONE
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-039-CATALOG-APPLY-COMMIT-BARRIER.md
CURRENT_BRANCH: main; Git is authority for moving HEAD

## Current truth

The exposure-only technical MVP is complete. The canonical workflow is
implemented, CI-certified and representative-live-verified through the final
Catalog/rerender boundary:

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

Lightroom is the authoritative renderer and Catalog-visible Develop state.
Python owns read-only preview-cache extraction, immutable package/session data,
decision validation, deterministic safety/convergence planning and render
freshness checks. External AI has decision-only authority. The canonical route
does not require XMP Save/Read Metadata synchronization.

## Technical MVP closure evidence

Automated/integration chain:

- WO-037 explicit Prepare / Import-Apply / Prepare Next package architecture is
  CI-certified on Windows/Python 3.12 and 3.13.
- WO-038 ordered contact-sheet package creation/integrity is integrated.
- WO-039 post-commit Catalog verification, absolute-target idempotency,
  fail-closed confirmation and legacy technical-state recovery passed CI run
  #91.
- Governance/instruction reconciliation commit `3c1ae399` passed GitHub Actions
  run #95 (`33355167400`) on Windows/Python 3.12 and 3.13.

Representative Lightroom chain on session `sess-1788136092`:

1. A 324-image live session reached real decision/apply behavior and exposed the
   original same-transaction stale-read defect.
2. After WO-039, `Import / Apply AI Results` recognized the 21 already-present
   absolute Catalog targets without a second delta and returned:

   ```text
   Verified Catalog applies: 21
   PASS: 303
   REVIEW: 0
   RERENDER_REQUIRED
   ```

3. After Lightroom rerender, `Prepare Next AI Package` created Pass 2 and
   returned `PACKAGE_READY` for the same session.

This closes both Roadmap Gate A and Gate B. A separate live multi-pass
convergence Work Order is not required merely to repeat deterministic behavior
already covered by automated/integration evidence.

## Capability boundary at closure

Live evidence now supports the real canonical path through:

- whole-folder/session identity;
- immutable package/decision handoff;
- real Catalog absolute `Exposure2012` target application;
- corrected post-commit confirmation and idempotent recovery;
- `RERENDER_REQUIRED` transition;
- fresh Pass 2 package creation.

Deterministic internals such as exact-set/schema validation, exposure bounds,
oscillation/no-progress and convergence/safe-stop rules continue to rely on
executed automated/integration evidence where a separate Lightroom repetition
would add no new capability proof.

## No active technical blocker

There is no active Work Order and no known blocker to the declared technical
MVP boundary.

The optional WO-031 diagnostic implementation still contains historical
XMP/metadata-sync aggregate readiness semantics. These are legacy diagnostic
debt and are not a prerequisite for the current Catalog-authoritative workflow.
They should be changed only if a future product requirement makes that
readiness report important again.

## Post-MVP backlog

The next phase is owner-selected product improvement, not automatic Work Order
continuation. Candidate areas remain:

1. AI exposure-judgment calibration with representative photographer review.
2. Operator UX and simpler session/error recovery.
3. Packaging/distribution for normal Windows + Lightroom installation/use.
4. Optional provider automation through isolated adapters.
5. Broader relevance/quality/culling only if explicitly required with suitable
   evidence beyond the current small previews.

No item above is active merely because it appears in the roadmap.
