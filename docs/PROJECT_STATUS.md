# Project Status

LAST_UPDATED: 2026-09-06
PROJECT_PHASE: POST_MVP_PRODUCT_IMPROVEMENT
CURRENT_WORK_ORDER: Work-Order/WO-041-SCENE-COMPLETE-EXPOSURE-ITERATION.md
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-043-DEVELOPMENT-HISTORY-AND-DOC-ARCHIVE.md
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


## Completed evidence upgrade — WO-042 Standard Preview reuse

The canonical package no longer uses the ~320 px RootPixels image as normal AI evidence. Python now resolves the Lightroom preview UUID + digest + orientation and copies an already-rendered cache tier with a 1440 px minimum target: exact 1440 if present, otherwise the smallest existing larger tier. Smaller-only caches return `PREVIEW_TIER_NOT_READY`; there is no silent fallback and no cache write/render request.

Real read-only cache evidence inspected 5,845 records (750 exact 1440, 1,714 larger fallbacks). The representative 34-image historical orientation selection had adequate cached evidence for every image; isolated canonical preparation reused 34 existing 1920 renders, produced 34/34 package previews with 26 landscape + 8 portrait outputs and three contact sheets. CAP-055 is INTEGRATED.


## Completed documentation reconciliation — WO-043

Root `DEVELOPMENT_HISTORY.md` now records the Work Order chronology and major architecture phases without becoming current execution authority. Clearly superseded duplicate notes/plans were moved, not deleted, to `archive/legacy-docs/`; `archive/README.md` maps each archived artifact to its current authority. Canonical Work Orders remain under `Work-Order/`, and maintained status/capability/evidence documents remain under `docs/`.

After this bounded documentation task, WO-041 resumes as the current Owner-live-validation gate.

## Pending Owner live gate — WO-041 scene-complete Exposure iteration

Owner testing selected a new post-MVP correctness gate after the technical MVP
and WO-040 closure. The issue is not Catalog mutation safety; it is photographic
coverage and iterative settlement.

Current implemented/integrated truth:

- every FOUND image is evaluation coverage; PASS explicitly means checked and no
  Exposure change needed;
- canonical session decisions require `scene_exposure_verdict` and
  `scene_delta_ev`, while Python validates only structural consistency;
- guidance no longer requires a fixed contact-sheet-first/anchor-first reasoning
  sequence; reference images are context, not proof of correct scene Exposure;
- later passes include the complete frozen session image set;
- added/removed/replaced Lightroom images fail closed as `SESSION_SCOPE_CHANGED`;
- stale adjusted previews return `WAITING_FOR_RERENDER`, do not mutate image
  status, and do not append a new pass;
- REVIEW remains re-evaluable and cannot by itself make a session converged;
- `SESSION_COMPLETE` requires all frozen-session images to be PASS;
- canonical Lightroom plug-in metadata is now version `1.2.11`.

Local focused/full pytest, integration, config smoke and compileall are green.
Read-only historical runtime inspection found `sess-1788499715` Pass 2 contained
184/315 images (131 omitted) and Pass 3 34/315; `sess-1788544053` Pass 2 contained
148/393 images (245 omitted) and recorded 13 stale hashes as photographic REVIEW.
These are defect-discovery evidence only; historical runtime was not modified.

**Pending live gate:** representative Owner-operated Lightroom validation with plug-in `1.2.11`. Until that passes, CAP-054 remains INTEGRATED and WO-041 remains `AWAITING_OWNER_VALIDATION`.

## Completed post-MVP gate — WO-040 preview orientation correctness

Owner review of real package `sess-1788482026` found sideways portrait previews
inside otherwise valid contact sheets. Read-only inspection proved the cache
orientation signal is carried by `ImageCacheEntry.orientation`: 26 representative
records are `AB` and 8 are `DA`; the extracted root-pixel JPEGs themselves carry
no EXIF Orientation tag.

WO-040 now:

- resolves UUID + orientation from the same read-only cache identity record;
- supports non-mirrored `AB`/`BC`/`CD`/`DA` rotations and fails closed on
  unsupported/mirrored values;
- preserves the raw `RootPixels` SHA-256 separately as render-freshness evidence;
- normalizes only the durable package JPEG before contact-sheet construction;
- records raw-render and normalized-artifact hashes in the immutable manifest while orientation is consumed deterministically during extraction.

Automated/focused/full/integration/config/compile/diff gates are green locally.
A read-only scratch re-extraction of the same 34 real cache identities returned
34 FOUND, 0 missing/ambiguous/failed, with 26 `(320, 213)` `AB` previews and 8
`(213, 320)` `DA` previews; exactly those 8 normalized artifact hashes changed,
while all 34 raw fingerprints matched the original package hashes.

**WO-040 live exit evidence:** normal Lightroom `Prepare AI Package` created `sess-1788485733` with 34/34 previews and 3 contact sheets. Runtime and Owner-uploaded contact-sheet SHA-256 values match exactly; visual inspection confirms all 34 images are in Lightroom-intended orientation. The pre-fix package remains immutable historical evidence.

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

## Technical MVP remains closed

There is no reopened technical-MVP blocker. WO-040 is closed `LIVE_VERIFIED`; it corrected the post-MVP visual-evidence boundary without changing the Catalog-authoritative MVP architecture or authorizing mutation.

The optional WO-031 diagnostic implementation still contains historical
XMP/metadata-sync aggregate readiness semantics. These are legacy diagnostic
debt and are not a prerequisite for the current Catalog-authoritative workflow.
They should be changed only if a future product requirement makes that
readiness report important again.

## Post-MVP backlog

WO-041 is the active owner-selected product-improvement gate. After it closes, remaining candidate areas include:

1. AI exposure-judgment calibration with representative photographer review.
2. Operator UX and simpler session/error recovery.
3. Packaging/distribution for normal Windows + Lightroom installation/use.
4. Optional provider automation through isolated adapters.
5. Broader relevance/quality/culling only if explicitly required with suitable
   evidence beyond the current small previews.

No item above is active merely because it appears in the roadmap.
