# Project Roadmap — Lightroom AI Exposure Assist

LAST_RECONCILED: 2026-09-06
CURRENT_PHASE: POST_MVP_PRODUCT_IMPROVEMENT
CURRENT_GATE: WO-041_SCENE_COMPLETE_EXPOSURE_LIVE_VERIFY

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

## Completed post-MVP gate — WO-040

**Goal:** make the visual evidence consumed by external AI preserve Lightroom's
intended display orientation without weakening read-only cache safety or render
freshness proof.

Current executed evidence:

- real `sess-1788482026` package exposed sideways portrait tiles despite valid
  identity/byte/package integrity;
- live read-only cache reconciliation found 26 `AB` and 8 `DA` records, with
  every known sideways example in the `DA` set;
- implementation now normalizes durable package previews while retaining a
  separate raw root-pixel render fingerprint;
- focused/full pytest, integration, config smoke, compileall and diff checks pass;
- read-only scratch extraction of all 34 representative identities produced
  34/34 valid previews and three valid contact sheets; only the 8 `DA` visual
  artifact hashes changed.

**Exit evidence:** fresh Lightroom session `sess-1788485733` produced 34/34 valid previews and 3 contact sheets; the Owner-uploaded sheets matched the runtime artifacts by SHA-256 and Controller visual inspection confirmed all 34 images in intended orientation. WO-040 is closed `LIVE_VERIFIED`.

## Active post-MVP gate — WO-041

**Goal:** make AI Exposure evaluation scene-complete without prescribing a fixed
reasoning recipe, and make iterative state settlement match photographic truth.

Implemented/integrated evidence now covers:

- PASS as genuine evaluated no-change, not forced mutation;
- explicit absolute scene verdict + scene correction signal in the canonical
  session decision contract;
- deterministic rejection of contradictory scene outcomes;
- complete frozen-image-set re-audit on later passes;
- session-scope drift rejection when Lightroom images are added/removed/replaced;
- stale adjusted previews becoming `WAITING_FOR_RERENDER` without REVIEW
  contamination or pass admission;
- convergence only when all frozen-session images are PASS;
- Lightroom messages that distinguish `SESSION_COMPLETE`, `RERENDER_REQUIRED`,
  `AI_RECHECK_REQUIRED`, and `WAITING_FOR_RERENDER`;
- plug-in version `1.2.11`.

Automated/full/integration/config/compile gates are green locally. Historical
read-only runtime reconciliation confirms prior sessions omitted already-PASS
images from later packages and could convert stale-render evidence into REVIEW;
the corrected algorithm addresses those exact conditions.

**Remaining exit gate:** Owner reloads plug-in `1.2.11` and performs a
representative Lightroom iterative run proving the new wait/re-audit/completion
behavior. WO-041 remains ACTIVE and CAP-054 must not be promoted beyond
INTEGRATED until that live proof exists.

## Post-MVP roadmap

WO-040 closed the preview-orientation correctness gap. The remaining directions stay backlog unless explicitly selected:

1. **AI judgment calibration** — preview orientation is now live-verified; broader photographer review, exposure tolerance/reference quality and model/provider comparison remain the next possible calibration work.
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

WO-041 is currently active. After its live exit gate closes, the Controller must identify the next Owner-selected
post-MVP goal and state:

1. which roadmap outcome it advances;
2. the genuinely new capability/product boundary being introduced;
3. why existing completed Work Orders do not already provide that capability;
4. the finite evidence that will make the new Work Order terminal.

A defect discovered while proving an active future gate remains with that Work
Order unless it is genuinely a new capability/boundary. Documentation truth
mismatches are reconciled during the owning task's closeout. Post-MVP ideas stay
in backlog until explicitly selected.

Do not activate a second Work Order while WO-041 remains active. After WO-041 closes, keep `CURRENT_WORK_ORDER: NONE` until the next gate is explicitly selected.
