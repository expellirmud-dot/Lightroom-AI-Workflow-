# RCV-002 — Renderer calibration and exposure-target correctness (started)

**Status:** ACTIVE / read-only diagnosis started 2026-10-27; automatic Exposure method **NOT** approved.
**Based on:** `RCV-001_PHOTOGRAPHIC_GATE_AUDIT.md` and the source-backed recovery roadmap.
**Scope:** current **local dirty** source on the authorized Windows PC is used as evidence only. Separate GitHub branch is a snapshot of old `main`; do not pretend it reproduces the local October implementation.

## Objective and narrow acceptance

Identify and test the real cause of wrong/inconsistent Exposure recommendations. In particular, determine whether creating a synthetic display-JPEG exposure candidate and mapping its measured brightness to Lightroom `Exposure2012` via reusable calibration samples preserves intended subject/skin/highlight rendering. Avoid changing code until a bounded falsification is available.

**DONE when** all of the following are evidenced (not by reports alone):
- [x] Trace actual production route candidate → target measurement → renderer-calibrated EV.
- [x] Read and hash-verify a bounded real Lightroom-preview subset with DARKEN/KEEP/BRIGHTEN/MIXED cases, recording descriptive display histograms.
- [ ] Obtain photographer-approved direction/acceptable outcome for positive, negative, zero and mixed-light controls (existing labels are provisional).
- [ ] Render actual **Lightroom** Before/After with recorded profile/preset, fixed WB, actual Exposure2012 and fresh preview generation; compare with the candidate prediction. No JPEG-only simulation presented as a Lightroom After.
- [ ] Produce exact regression test that reproduces a demonstrated defect in the active calculation path, then implement the smallest warranted fix; independent reviewer examines regression and new renderer evidence.
- [ ] RCV-001 gate remains blocking until real photographic acceptance. No whole-album auto apply.

## Read-only source review — evidence

Local worktree sources reviewed (not the stale GitHub `main` copy):

1. `src/lr_ai_exposure/reference_free_target.py`: `build_reference_free_target_package` makes synthetic display-JPEG brackets. They are constructed by decoding the JPEG sRGB channels, multiplying linearized RGB, clipping and re-encoding. This is useful for candidate appearance **but not** a native Lightroom RAW Exposure render.
2. `src/lr_ai_exposure/production_job.py` lines ~1725–1774: `_reference_free_target_measurement` creates a new synthetic JPEG using `simulated_display_ev`; measures the **previously frozen skin ROIs** on that JPEG; rejects candidate highlight fractions `>0.005` beyond baseline. This is a protective heuristic, not proof of RAW highlight retention.
3. `production_job.py` lines ~1900–1990: uses `estimate_renderer_calibrated_delta_ev` against target measurements; when the strategy is skin/face, the supplied calibration samples are `VLD202_RENDERER_CALIBRATION_SAMPLES` (else `VLD205_SCENE_RENDERER_CALIBRATION_SAMPLES`). Candidate EV itself is not written directly. The **validity/generality** of these historical calibration samples for today's cameras/styles/light conditions remains an experiment, not a proven universal mapping.
4. `hybrid_exposure.py` lines ~703–786: derives positive measurement-per-EV slopes from real-render samples and interpolates by baseline measurement, then quantizes/bounds. Its mathematical checks do not guarantee **photographic appropriateness of the target**, subject selection, or highlight details.
5. `production_job.py` ~1318–1400: reference-free path declines `ROBUST_SCENE_LUMINANCE` fallback, needs valid YOLO skin/face ROIs and returns median over usable faces. A median over faces may fail when intended subjects differ or are in mixed light. This is **risk to test**, not a proven current defect.

## Bounded diagnostic executed now — real cached JPEGs, read-only

Source: historical Oct 9 `fullsize-review-progress.json`. Seven selected existing Lightroom-rendered preview JPEGs were read again and their SHA-256 hashes matched their frozen review records **7/7**. `analyze_display_histogram` was run on the actual decoded JPEG bytes; no photo file was modified.

| Image stem | Provisional review | Display JPEG Y' median /255 | Fraction any RGB ≥245 | Note |
|---|---|---:|---:|---|
| PTO_4919 | KEEP candidate | 207 | 0.05238 | high-key scene can legitimately be bright |
| PTO_9147 | KEEP candidate | 205 | 0.01300 | acceptable according to provisional review |
| PTO_4995 | KEEP candidate | 100 | 0.00184 | dark scene may be intentionally dark |
| PTO_9197 | DARKEN candidate | 235 | 0.48770 | strongly bright displayed scene |
| PTO_9271 | DARKEN candidate | 242 | 0.67892 | strongly bright displayed scene |
| PTO_9327 | MIXED LIGHT / UNCERTAIN | 197 | 0.20401 | large bright-region fraction, foreground subject review ambiguous |
| PTO_9419 | BRIGHTEN candidate | 63 | 0.00242 | underlit foreground according to provisional review |

The numbers are **display-domain brightness**; this uses Rec.709 weights on gamma-encoded JPEG RGB, not physical scene-linear luminance or proof of actual RAW saturation. These seven images illustrate why *a global clipping/median threshold alone cannot certify Exposure decisions*; they do not establish any production threshold or photo quality ground truth.

## Work plan, review protocol and stop conditions

- **RCV-002-A — DONE:** trace the exact route from the current local code; verify real preview bytes/hashes for a frozen subset. Controller executed; no CLI worker and no Lightroom UI input.
- **RCV-002-B — NEXT:** choose a minimal pre-registered control matrix: two provisional DARKEN cases, one BRIGHTEN, two KEEP, one MIXED LIGHT; require explicit photographer confirmation of their intended direction, not invented EV targets. Source identities, hashes, baseline Process Version, Camera Profile, WB and actual Catalog Exposure2012 must be captured before any new image write.
- **RCV-002-C:** compare *real Lightroom* renderer responses for approved isolated targets. Need a safe sandbox/offline renderer plan and separate authorization before any Catalog/XMP mutation; if that boundary cannot be met, stop with reason and never substitute synthetic JPEGs.
- **RCV-002-D:** write one RED reproduction and bounded source fix **only if** the evidence isolates a testable failure (calibration, target, face ROI, or semantics). Code review plus focused tests + unchanged-good controls, exact Git diff, and isolated remote commit. No broad dirty-tree commit.
- **STOP:** if no reliable renderer evidence, no owner target, stale preview hash, different WB/profile, or other ambiguity, issue `UNRESOLVED` instead of a purported `PASS`.
- **Forbidden:** modifying real photos, live Catalog, .lrdata, XMP, current active WO, untracked local owner work, or bulk AI reruns.

**Product acceptance remains RED/UNKNOWN until RCV-002-C and roadmap R3–R5 pass.** 
