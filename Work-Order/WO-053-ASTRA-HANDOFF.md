# Astra continuation handoff — WO-053

Date: 2026-09-10. Scope: diagnosis/design handoff, not implementation completion.
Parent: `Work-Order/CURRENT_WORK_ORDER.md` and its active WO-053. This is an
Owner-requested subordinate task packet, not a new Work Order or replacement
for canonical status, architecture, or validation documents.

## Owner intent and authority

- Address the Owner as เจ้านาย; communicate in concise Thai.
- Make album exposure visually consistent, especially the subject/skin, using
  Exposure2012 only. Preserve all other Develop settings and original files.
- Owner authorizes bounded technical decisions and this handoff commit.
- Do not interpret this as permission to commit inherited changes or push.
- Initial and residual real Lightroom writes still require their separate
  explicit Owner confirmations through CatalogApplyBarrier.
- Owner permits AGY/Hermes CLI assistance; parallelism is optional, at most two
  agent threads. Do not introduce orchestration merely because it is available.

## Verified diagnosis from the preceding investigation

Evidence root: `runtime/jobs/job-1789032689` (local, not committed).

- 752 images; final persisted accounting: 432 ADJUSTED, 232 NO_CHANGE,
  88 UNRESOLVED. COMPLETE describes workflow accounting, not photographic quality.
- Initial plan: 433 WILL_ADJUST, 232 NO_CHANGE, 87 UNRESOLVED. Initial apply
  receipts report all 433 APPLIED_VERIFIED; residual receipts report 30.
  These are archived receipts, not a new observation of the live Catalog.
- All 752 baseline measurement entries used ROBUST_SCENE_LUMINANCE.
  All 202 group references had visual NO_CHANGE; another 30 images received
  deterministic zero delta. This describes this old job, not every current route.
- Example image ID 4208582, PTO_8855.NEF, group G055: reference 4208583,
  PTO_8856.NEF. Exposure moved 0 -> +1.00 -> +1.25. Baseline scene metric
  0.7565365433692932, target 0.9285043478012085, final 0.9206832051277161.
  Numeric verification accepted the result, while visual inspection found
  washed-out subject/highlight detail. The reference has a large white wall.
- Baseline: `previews/000192__PTO_8855.jpg`; reference:
  `previews/000193__PTO_8856.jpg`; final:
  `fresh-previews/000011__PTO_8855.jpg` under the evidence root.
  Final SHA-256: `58b820599c81a2bdeccf2b8d81d25a24fcc55cebd5dba9be1baed2d2d864cd1c`.
- The inspected scene meter trims/crops a display-JPEG luminance distribution;
  it does not identify the intended subject. Matching it can reward the wrong
  appearance. Near-white JPEG pixels do not prove clipping in the original RAW.
- No timing attribution was established. This job records one semantics run;
  do not claim an endless model loop based on the Owner's latency report alone.

## Decision: reuse, then falsify before another album run

Do not rebuild the plug-in, switch providers as a presumed fix, or rerun the
whole album. Retain identity, render extraction, absolute targets, drift checks,
sole writer, durable accounting and the one-residual limit.

Current WO-053 VLD-203/204 already specifies reference-free per-image target
intervals, canonical subject ROIs and empirical renderer response. Reuse it.
`src/lr_ai_exposure/reference_free_target.py` already contains synthetic JPEG
brackets; these are target proposals, NOT actual Lightroom exposure renders.
Do not reintroduce a master reference as photographic authority, a shared group
delta, numeric EV from AI, or a global scene median as a subject substitute.

First reconcile the reachable route with current authority: the old job used
scene-reference semantics, while the current pointer claims new packages reject
legacy semantics. Archived job evidence alone does not prove a current router bug.
Read callers in `main.py` and `production_job.py`; test the actual new-package
path and its baseline/fresh measurement strategies before proposing a patch.

## Bounded next task for Astra or Antigravity

1. Refresh HEAD, pointer and relevant dirty state. Read project-read-first and
   applicable visual skills. Preserve local work; inspect existing reference-free
   tests before writing another implementation. Do not repeat broad repo discovery.
2. Trace new package -> semantic intake -> ROI measurement -> absolute plan ->
   adjusted-only verification. Establish whether scene fallback is reachable on
   the new reference-free path. Report VERIFIED / INFERENCE / UNKNOWN separately.
3. Make one non-mutating scratch experiment using an explicitly enumerated small
   subset of frozen evidence, including the failure above and already-good controls.
   Cover white background, backlight, mixed framing/lighting and lens changes where
   metadata permits. Never rewrite the old job to make it look successful.
4. Give a fresh visual worker only authorized images, opaque IDs, task and schema;
   no known correction values, debugging narrative or preferred answers. Require
   proof it actually received images. One bounded pass; failures stay unresolved.
   This known failure set is regression evidence, not blind generalization proof.
5. Accept only subject-appropriate targets, preservation of important detail and
   no regression of good controls. Group consistency is secondary to individual
   correctness. Ambiguous subject/ROI or model disagreement must fail closed.
6. If a defect is proven, agree the narrow affected seam in WO-053, RED once,
   minimal repair, focused GREEN and relevant regression. At most two failed
   fix/retest attempts. Reconcile canonical documents after actual behavior proof.
7. Only after offline acceptance: request the existing separate Owner confirmation
   for a fresh representative approximately 50-image Lightroom proof. Inspect actual
   fresh renders of adjusted images; metric convergence is not visual acceptance.
   Allow only the existing one separately confirmed residual; no whole-album loop.

Stop with exact evidence if image delivery, trustworthy subject measurement,
renderer calibration or host access is missing. Do not silently replace the
missing capability with a global brightness heuristic or invented visual verdict.

## Available tools and limits observed

- AGY installed at `%LOCALAPPDATA%/agy/bin/agy.exe`; `agy models` succeeded.
  CLI help exposes plan mode, bounded print timeout and structured output.
- Hermes installed at `%LOCALAPPDATA%/hermes/bin/hermes.exe`.
  Local provider model cache includes `muse-spark-1.3-contributor-free` under
  opencode-free, alongside other entries. Cache presence is NOT proof of current
  availability, free quota or vision support. Verify provider metadata and one
  bounded image request before assigning a photographic batch. Do not dump auth,
  environment files or credentials; do not change the configured default model.
- No CLI visual experiment was executed in this investigation.
- Native Computer Use connection failed with native pipe unavailable / OS error 2.
  Do not claim Lightroom is controllable until a fresh connection succeeds.
- Astra's remaining account quota/reset time is not observable here. No background
  worker, automatic five-hour resumption or Antigravity delegation was started.

## Delivery and resumption caveat

Investigation base HEAD: `0654ecc57ae24f30cb03dab67d283f1c48cb593a`, branch main.
There were 159 pre-existing dirty status entries and an empty index before this
handoff. Many active Work Order/source/test artifacts are local-only or modified.
This commit intentionally contains only this note: it is NOT a portable snapshot
of the working implementation. Resume in this same workspace; a clean checkout
elsewhere will not reproduce all the local code or runtime evidence.

No production code, Lightroom state or historical job was changed for this
handoff. No implementation tests were run for this documentation-only delivery.
Validate handoff paths, diff hygiene, exact single-file commit scope and preservation
of inherited dirty status. Do not promote WO-053 or claim the album is fixed.
