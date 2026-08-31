# Project Roadmap — Lightroom AI Exposure Assist

LAST_RECONCILED: 2026-08-31
CURRENT_PHASE: MVP_CLOSURE_LIVE_CERTIFICATION
CURRENT_GATE: Work-Order/WO-039-CATALOG-APPLY-COMMIT-BARRIER.md

## Product destination

Deliver a Windows-first Lightroom Classic exposure assistant that can, for one
source folder, prepare Lightroom-rendered evidence, obtain provider-neutral AI
exposure decisions, apply only guarded Catalog `Exposure2012` targets, prove a
fresh rerender, and iterate under deterministic convergence/safe-stop rules
without modifying original photographs or Lightroom database files directly.

The current MVP is exposure-only. AI provider/model quality, broader image
quality/culling, packaging polish, and optional transport automation are not
required to close the technical MVP.

## Current position

The canonical architecture and core implementation are already in place:

```text
Diagnose Current Folder
→ Prepare AI Package
→ external AI / deterministic test decisions
→ Import / Apply AI Results
→ Lightroom Catalog Exposure2012 confirmation
→ RERENDER_REQUIRED or SESSION_COMPLETE
→ Prepare Next AI Package after rerender
```

WO-037 established the explicit filesystem package boundary, WO-038 added
contact-sheet package integrity, and WO-039 hardens the real Lightroom Catalog
commit/verification boundary discovered during live use.

This phase is therefore **closure and live certification**, not open-ended
feature development.

## Gate A — Close WO-039 Catalog verification

Using the existing affected live session, the current gate closes only when:

1. `Import / Apply AI Results` is re-run with the WO-039 fix.
2. The 21 targets already present in Lightroom are recognized idempotently and
   are not adjusted a second time.
3. Legacy technical `REVIEW` state is repaired only from failed apply evidence.
4. The observed result is `Verified Catalog applies: 21`, `PASS: 303`,
   `REVIEW: 0`.
5. The session ends at `RERENDER_REQUIRED`, not false convergence.

Until this evidence exists, Catalog post-commit verification remains
`INTEGRATED`, not `LIVE_VERIFIED`.

## Gate B — Prove the next render generation

After Gate A and Lightroom rerender:

1. Run `Prepare Next AI Package` for the same session/folder.
2. The render freshness barrier must accept only a genuinely refreshed preview
   generation.
3. Stale/unproven previews must fail closed.
4. The next immutable pass must reach `PACKAGE_READY` without re-applying the
   prior pass.

This is the final known live technical gate for the MVP iterative boundary.

## Technical MVP closure

If Gate A and Gate B succeed, automated/integration evidence remains green, and
no new safety/correctness blocker appears, the Controller should close WO-039,
reconcile project truth and move the phase to `TECHNICAL_MVP_COMPLETE`.

Closure is based on the **combined evidence chain**, not a requirement that every
internal rule be separately re-proven in Lightroom:

Live/representative evidence must cover:

- whole-folder/session identity reaching the real workflow;
- decision import reaching real Catalog apply;
- guarded absolute `Exposure2012` targets observed in Lightroom;
- corrected post-commit confirmation;
- rerender transition and fresh next-pass preparation.

Automated/integration evidence may continue to prove deterministic internals
such as exact-set validation, package/contact-sheet integrity, exposure bounds,
oscillation/no-progress and convergence/safe-stop logic.

A separate Work Order for a multi-pass live convergence demonstration is **not
required merely to repeat deterministic behavior** after Gate B. Create further
technical work only if Gate A/B exposes a real defect or the Owner explicitly
requires additional live certification.

Closure also requires `AGENTS.md`, `PROJECT_STATUS.md`, `CAPABILITY_MATRIX.md`,
`VALIDATION_REGISTER.md`, `DECISIONS.md`, this roadmap, and the active Work
Order pointer to agree with the evidence.

## Post-MVP roadmap

After technical MVP closure, evaluate these in order of demonstrated need:

1. **AI judgment calibration** — representative photographer review, exposure
   tolerance/reference quality, model/provider comparison.
2. **Operator UX** — clearer package/session state, error recovery, fewer
   manual steps, understandable apply/review feedback.
3. **Packaging/distribution** — installation, upgrades, diagnostics and release
   packaging for normal Windows/Lightroom use.
4. **Optional provider automation** — isolated adapters only when they improve
   practical use without coupling the core to one vendor.

These are roadmap backlog items. They do not become active Work Orders merely
because they are listed here.

## Work Order activation rule

A failure discovered while proving the current acceptance gate does **not**
automatically justify a new Work Order.

Default classification:

- defect inside the current gate/capability → remediate under the current Work
  Order;
- stale/conflicting project documentation → reconcile during current closeout;
- genuinely new capability, architecture boundary, safety model, or owner
  product requirement → may justify the next Work Order;
- post-MVP improvement → keep in roadmap backlog until the current phase exits.

Before activating a new Work Order, the Controller must state:

1. which roadmap gate it advances;
2. why the active Work Order cannot own the work safely;
3. what new capability or boundary is introduced;
4. the evidence that will make the new Work Order terminal.

If those answers are not clear, do not create another Work Order.
