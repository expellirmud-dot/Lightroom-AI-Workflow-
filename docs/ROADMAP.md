# Project Roadmap — Lightroom AI Exposure Assist

LAST_RECONCILED: 2026-08-31
CURRENT_PHASE: TECHNICAL_MVP_COMPLETE
CURRENT_GATE: NONE

## Product destination

Deliver a Windows-first Lightroom Classic exposure assistant that can, for one
source folder, prepare Lightroom-rendered evidence, obtain provider-neutral AI
exposure decisions, apply only guarded Catalog `Exposure2012` targets, prove a
fresh rerender, and iterate under deterministic convergence/safe-stop rules
without modifying original photographs or Lightroom database files directly.

The technical exposure-only MVP reached this destination on 2026-08-31. Future
AI quality, broader image triage, UX, packaging and provider automation are
post-MVP product work rather than missing technical closure gates.

## Technical MVP closure — achieved

The implemented canonical flow is:

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
contact-sheet package integrity, and WO-039 hardened and live-verified the real
Lightroom Catalog commit/verification and rerender transition.

### Gate A — COMPLETE

Using real session `sess-1788136092`, the Owner re-ran
`Import / Apply AI Results` with the WO-039 fix. Lightroom reported:

```text
Verified Catalog applies: 21
PASS: 303
REVIEW: 0
RERENDER_REQUIRED
```

The 21 already-present absolute targets were recognized idempotently, legacy
technical REVIEW contamination was repaired, and the session did not falsely
converge.

### Gate B — COMPLETE

After Lightroom rerender, `Prepare Next AI Package` on the same session
successfully created Pass 2 and returned:

```text
PACKAGE_READY
Session: sess-1788136092
Pass: 2
```

This proves the representative iterative transition through corrected Catalog
confirmation, rerender freshness acceptance and next immutable package
creation.

### Automated closure evidence

The runtime implementation remained green through WO-039 CI, and the reconciled
project/instruction state at commit `3c1ae399` passed GitHub Actions run #95
(`33355167400`) on Windows/Python 3.12 and 3.13.

The combined evidence chain is sufficient for `TECHNICAL_MVP_COMPLETE`.
Deterministic internals do not require separate Lightroom repetition when their
behavior is already covered by executed automated/integration evidence and no
new live boundary would be proven.

## Post-MVP roadmap

These are backlog directions, not active Work Orders:

1. **AI judgment calibration** — representative photographer review, exposure
   tolerance/reference quality and model/provider comparison.
2. **Operator UX** — clearer package/session state, error recovery, fewer
   manual steps and understandable apply/review feedback.
3. **Packaging/distribution** — installation, upgrades, diagnostics and release
   packaging for normal Windows/Lightroom use.
4. **Optional provider automation** — isolated adapters only when they improve
   practical use without coupling the core to one vendor.
5. **Broader visual triage** — relevance, duplicates, blur/focus/quality or
   keep/cull only if a future product requirement supplies suitable evidence
   and explicitly activates that task.

## Next Work Order activation rule

There is currently no active Work Order. Do not manufacture one simply to keep
execution moving.

Before activating the next Work Order, the Controller must identify an
Owner-selected post-MVP goal and state:

1. which roadmap outcome it advances;
2. the genuinely new capability/product boundary being introduced;
3. why existing completed Work Orders do not already provide that capability;
4. the finite evidence that will make the new Work Order terminal.

A defect discovered while proving an active future gate remains with that Work
Order unless it is genuinely a new capability/boundary. Documentation truth
mismatches are reconciled during the owning task's closeout. Post-MVP ideas stay
in backlog until explicitly selected.

If those conditions are not met, keep `CURRENT_WORK_ORDER: NONE`.
