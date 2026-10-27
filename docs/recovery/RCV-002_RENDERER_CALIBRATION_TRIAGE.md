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

## Follow-up executed 2026-10-27 — Numeric calibration support guard (safe experiment)

**RESEARCH GATE: test-only code delivered; production integration and photographic acceptance remain BLOCKED.**

- Retrieved and re-read all seven local project `SKILL.md` files and mandatory `AGENTS.md`, `docs/INDEX.md`, active Work Order pointer and WO-057 authority before this task. Serena/CodeGraph: NOT_REQUIRED for the bounded symbols and tests inspected.
- **Actual risk reproduced:** `VLD202_RENDERER_CALIBRATION_SAMPLES` includes measured baseline range **0.518295–0.832298**. Unmodified `estimate_renderer_calibrated_delta_ev` gives **+0.30 EV** for baseline 0.30 → target 0.38, and **−0.65 EV** for baseline 0.95 → target 0.85, outside sampled baseline support. These are extrapolations without local evidence, not automatically erroneous pictures.
- **Historical actual job:** `runtime/jobs/job-1789004603/measurement-results.json`: 49 `MEASURED` records examined; **7 below VLD202 baseline numeric support and 0 above**. No photo has been changed. This is a support-risk count, not necessarily seven bad exposure outputs.
- **Proposed fail-closed protection:** `tools/renderer_calibration_support.py` rejects baseline outside observed range and target outside the combined observed rendered-measurement range before delegating to the unchanged numeric EV estimator. Returns exceptions; no mutation/EV authority, no machine learning, no catalog effects. Its tests live in `tests/test_renderer_calibration_support_recovery.py`. Delivered via GitHub contents API into this isolated recovery branch, not via local dirty Git staging. Verified source blobs by `fetch_file`.
- **Test scope:** 9 local unit tests PASS; 3 more real-estimator integration tests PASS against the 10 frozen VLD202 sample records (in-support original and guarded results identical; low/high out-of-support are rejected without calling original estimator); 12 existing `test_renderer_response_calibration_live_evidence.py` tests PASS.
- **Planner injection proof:** In an isolated local pytest fixture, the guard was temporarily monkeypatched into the *actual current local* `production_job.build_production_plan` estimator seam. **3/3 PASS**: baseline 0.30/target 0.38 and baseline 0.95/target 0.85 both produce `UNRESOLVED`, `reason_code=RENDER_RESPONSE_UNCERTAIN`, `catalog_plan.planned_count=0`; baseline 0.60/target 0.65 remains `WILL_ADJUST` and produces one planned item. **No production source edit took place.** The portable test-only reproduction is archived at `docs/recovery/experiments/test_planner_guarded_injection.py`, deliberately outside automatically collected production tests pending clean-checkout dependency closure.
- **Photographic renderer gap:** An earlier independent read-only script matched **8 of 10** actual historical Lightroom Before/After preview hash pairs; the other 2 original early-After files are not retained. Example real vs synthetic JPEG `any RGB >=245` fraction: `PTO_3872` (+0.20 EV) **0.02728 vs 0.04721**; `PTO_3888` (−0.30 EV) **0.00438 vs ~0.00008**. These demonstrate different render responses, not proof of which looks better.
- **Review boundary:** The new range test is a *necessary guard* only; it cannot prove matching camera/profile/preset/white balance/ROI provenance or photographer-accepted look. Do not use its passing tests as image quality certification, and do not enable it in live Catalog or offline XMP automatic mutation without an active authorized release gate.
- **Repository status:** Local `main` HEAD remains `17491925a522`, about 196 modified/untracked paths with an old `.git/index.lock`; none reset, staged, removed, or committed. The release-precedence conflict with active **WO-057 G0 BLOCKED** persists. The GitHub recovery branch is the only delivery target.

**Next:** isolate source dependency closure safely; integrate this check into the exact actual planner call site with stable `RENDER_RESPONSE_UNCERTAIN` reason; verify targeted old regressions and safe unchanged controls; seek fresh *actual Lightroom renderer* comparison/owner photographic approval before any real image write or product acceptance.

## Follow-up read-only KEEP risk triage (2026-10-27)

This next experiment addresses the **observed all-KEEP 24/24 failure**, without treating display JPEG histograms as photo correction authority.

- New portable read-only CLI: `tools/photo_exposure_risk_triage.py`, with `tests/test_photo_exposure_risk_triage.py`. All five synthetic safety/unit tests PASS (bright vs dark vs ordinary, stale source SHA rejection, duplicate ID rejection, path escape rejection, sample coverage rejection). CLI works on the original 24/24 frozen SHA-verified Lightroom previews.
- Exploratory / not independently validated thresholds: `fraction any RGB >=245 >= 0.15` **OR** `display Rec.709 weighted sRGB median <= 80/255`. Thresholds were chosen with the *known failed cohort in view* and must **not** be promoted as evidence from a blind holdout.
- Trial result: **24/24 source hashes matched**; **9/24 flagged `REVIEW_REQUIRED`**, including all three known independent review candidates `PTO_9197`, `PTO_9271`, `PTO_9419`. The other 6 are **review requests only**, not confirmed wrong exposure. CLI audit reported `accepted_as_photographic_quality=false`, `numeric_ev_authority=NONE`, `catalog_xmp_mutation_authority=NONE`. CLI exit 2 means intentional review required, not processing failure; harness verified those expected results with exit 0.
- Measured on the authorized Windows computer: historical custom diagnostic measured 24 images in **3.586 seconds**; standalone CLI process with JSON file/PowerShell inspection completed in **5.72 seconds**. Neither number is a whole-album or full workflow performance benchmark.
- The triage tool avoids a repeat of unconditional all-KEEP silently certifying a batch *when the risk-check stage is invoked*, but can flag genuine high-key, low-key, backlit or mixed-light photographs. **Never turn its histogram flags directly into Exposure EV corrections or automatic rejection.**
- GitHub source and tests exist only on the **isolated recovery branch**; the local dirty `main` and live Lightroom operating mode were not modified. Production integration needs a single active Work Order and WO-057 clean-checkout dependency closure first.

### Open gates

1. Isolated proposed calibration guard and review-risk CLI have source, tests, and replay evidence; **neither is wired into production**. Photo quality remains unverified.
2. Run review-risk tool on a genuinely unseen control/holdout set with visual or photographer-accepted references. Measure false alerts, missed true problem cases and processing speed. Do not tune against the held-out answers.
3. Validate real **Lightroom RAW renderer** Before/After in a safe isolated Catalog with exact preset, Camera Profile, WB and recorded Exposure2012; obtain a photographer-accepted exposure outcome.
4. Only after safe production dependency integration and scoped review: activate these checks in the intended workflow, run full tests, clean checkout proof, Commit/Push, and acceptance.

**No autonomous background continuation or unseen Lightroom operations have been scheduled.**
