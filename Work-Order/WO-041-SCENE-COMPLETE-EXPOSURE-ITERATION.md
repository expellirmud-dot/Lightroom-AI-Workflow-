# WO-041 — Scene-Complete Exposure Judgment & Iteration Safety

STATUS: ACTIVE
ACTIVATED: 2026-09-06

## Trigger

Owner testing found that an exposure session can appear operational while still producing incomplete photographic outcomes: some already-PASS images disappear from later-pass review, stale Lightroom previews can be converted into photographic REVIEW state, and the AI contract emphasizes anchor/reference harmony without requiring an explicit absolute scene-exposure conclusion. The Owner also clarified that complete coverage means every image is genuinely evaluated, **not** that every image must be adjusted.

The current working tree already contains Owner-reviewed/uncommitted post-WO-040 orientation changes and AI-guidance edits made during prior local work. Those edits are the accepted baseline for this Work Order; they must be preserved and reconciled rather than discarded.

## Roadmap outcome

Activate the post-MVP **AI judgment calibration + operator correctness** seam required before broader UX polish: make each iterative pass photographically complete, scene-aware, and state-safe while keeping the provider-neutral filesystem boundary and Catalog-authoritative Exposure2012 architecture.

## Goal

For one frozen Lightroom source-folder session, ensure that:

- every image remains eligible for genuine re-evaluation on later passes;
- PASS means "evaluated and no adjustment needed", not "skipped";
- AI records an explicit absolute exposure verdict for each scene context without being forced into a prescribed step-by-step reasoning method;
- Python validates complete/consistent scene-result structure but does not become the photographic judge;
- stale/unproven rerender evidence waits/fails closed without contaminating photographic REVIEW state;
- session convergence means all images have a photographic PASS, while unresolved REVIEW remains non-mutating and non-converged;
- a changed Lightroom image set cannot silently continue an existing frozen session;
- Lightroom user-facing state distinguishes COMPLETE, RERENDER_REQUIRED, and unresolved recheck/wait states clearly.

## Current truth

- Technical MVP remains complete; WO-040 is closed LIVE_VERIFIED.
- No Work Order was active when this Owner-selected post-MVP gate was activated.
- Current `SinglePassDecision` has per-image `scene_group_id` / `is_reference`, but no explicit absolute scene-exposure verdict.
- Pass >1 selection currently narrows to prior `ADJUST` images plus PASS references, which can exclude prior PASS images from re-audit.
- Render freshness currently mutates stale/unproven `ADJUST` images into photographic `REVIEW`.
- Convergence currently treats `PASS` and `REVIEW` as settled, allowing `is_converged=true` with unresolved photographic REVIEW.
- `runtime/` is ignored by Git and remains local session evidence.
- Lightroom plug-in metadata currently reports version 1.2.0 build 1.

## Authorized scope

Implementation:
- `src/lr_ai_exposure/ai_judge.py`
- `src/lr_ai_exposure/providers/manual_app.py` only if needed for new-decision validation
- `src/lr_ai_exposure/providers/google_vision.py` only to keep the optional provider adapter aligned with the provider-neutral decision contract
- `src/lr_ai_exposure/session.py`
- `src/lr_ai_exposure/session_lifecycle.py`
- `src/lr_ai_exposure/convergence.py`
- `src/lr_ai_exposure/render_barrier.py`
- `lightroom-plugin/AIExposureAssist.lrplugin/Info.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/DiagnoseCurrentFolder.lua` only to keep the reported plug-in version synchronized with metadata
- `lightroom-plugin/AIExposureAssist.lrplugin/PrepareNextAIPackage.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/ImportApplyAIResults.lua`

AI contract/guidance:
- `.agents/skills/exposure-judgment/SKILL.md`
- `.agents/skills/batch-consistency-review/SKILL.md`
- `docs/AI_JUDGE_CONTRACT.md`

Focused tests directly covering these behaviors under `tests/`.

Evidence / reconciliation:
- `Work-Order/WO-041-SCENE-COMPLETE-EXPOSURE-ITERATION.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/DECISIONS.md`
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `README.md` only if canonical user commands materially change

## Forbidden

- no direct `.lrcat` / `.lrcat-wal` / `.lrcat-shm` access
- no `.lrdata` writes
- no RAW/JPEG original or XMP mutation
- no real Lightroom Catalog Develop mutation during automated validation
- no external AI/API calls
- no provider-specific core coupling
- no culling/relevance/blur/focus/quality scope expansion
- no resident provider polling/listener
- no automatic export
- no destructive Git operations, commit, push, install, or deploy
- no rewriting existing immutable runtime passes

## Required behavior

1. **Coverage is evaluation, not mutation.** Every in-scope image receives a decision. `PASS` is a successful evaluated no-change result with `delta_ev=0`; the system must never encourage adjustment merely to demonstrate coverage.
2. **Explicit absolute scene conclusion.** New decisions expose a scene-level exposure verdict (`TOO_DARK`, `BALANCED`, `TOO_BRIGHT`, or `REVIEW`) plus an approximate shared scene correction signal. Python validates structural consistency within a `scene_group_id`; AI retains photographic authority over the verdict/value.
3. **Scene-complete later passes.** Later pass packages include the complete frozen session image set so prior PASS images can be re-audited when a scene conclusion changes. Render freshness remains required only for images actually adjusted in the prior confirmed state.
4. **Frozen session scope.** Preparing Pass >1 requires the current Lightroom selection snapshot to match the session's frozen identity/path set. Added/removed/replaced images fail closed with a clear "start a new session" condition.
5. **Rerender wait is technical state.** Unchanged/stale preview hashes or other render-freshness failures must not mutate image status to photographic REVIEW. A next pass is not admitted until required adjusted previews are fresh; an incomplete attempted pass is not appended as durable session lineage.
6. **REVIEW is unresolved, not success.** Existing photographic REVIEW may be re-evaluated in a later pass. `is_converged=true` only when every session image is photographic PASS. Maximum-pass or unresolved REVIEW outcomes stop safely but are not labeled converged.
7. **No-change pass semantics.** If a pass has no ADJUST decisions but has unresolved REVIEW, no rerender is required. The UI must distinguish unresolved recheck from `RERENDER_REQUIRED`.
8. **Plug-in version visibility.** Because canonical Lightroom command behavior changes under WO-041, `Info.lua` version is bumped to `1.2.11` so the Owner can verify the installed/reloaded plug-in revision.
9. Existing safety boundaries, absolute Catalog targets, provider-neutral package ownership, pass immutability, and exact-set validation remain intact.

## Acceptance evidence

Automated / integrated:
- decision-schema tests prove PASS=no-change and the new scene-level fields/semantics;
- group validation rejects contradictory absolute scene verdict/correction values within the same `scene_group_id`;
- later-pass package test proves all frozen session images are included, including prior PASS and REVIEW images;
- scope-drift test rejects added/removed/replaced Lightroom images before admitting a next pass;
- render-barrier tests prove stale preview evidence leaves photographic state unchanged and causes WAIT/fail-closed package preparation rather than REVIEW contamination;
- convergence tests prove REVIEW is re-evaluable and cannot produce `is_converged=true`; all-PASS can converge;
- no-adjust + unresolved-review result does not require rerender;
- plug-in static tests prove user-facing wait/recheck state and version `1.2.11`;
- focused tests pass;
- full pytest passes (environmental documented skips allowed);
- config smoke, integration tests, compileall and `git diff --check` pass.

Representative runtime evidence (read-only/local only):
- inspect at least one existing session that previously showed PASS exclusion / stale-render REVIEW contamination and confirm the corrected algorithm would classify those conditions as re-audit / WAIT rather than photographic completion. Do not rewrite the historical session.

Live Lightroom exit gate:
- Owner reloads plug-in version `1.2.11` and prepares/continues a representative session;
- after an Exposure2012 apply, an early Prepare Next attempt either waits clearly for stale previews without converting images to REVIEW, or proceeds only when required rerenders are fresh;
- next accepted pass includes the complete frozen image set and unresolved images remain re-evaluable;
- final `SESSION_COMPLETE` is shown only when all images are photographic PASS.

## Executed evidence so far

- Focused WO-041/session/render/plugin regression tests pass; the initial RED
  failures captured old REVIEW-render expectations and stale version assertions.
- Full pytest exits 0 with two expected skips.
- `--check-config` exits 0 (`manual_app`, dry-run configuration intact).
- `tests/integration` passes 6/6.
- `python -m compileall -q src tests` exits 0.
- `git diff --check` exits 0; only expected LF/CRLF warnings are emitted.
- Read-only runtime reconciliation: `sess-1788499715` froze 315 images but its
  historical later packages contained 184 then 34; `sess-1788544053` froze 393
  images but Pass 2 contained 148 and converted 13 unchanged preview hashes into
  photographic REVIEW. No historical runtime artifact was modified.
- Plug-in metadata and diagnostic reporting identify the changed behavior as
  version `1.2.11`.
- README was reviewed: canonical command names are unchanged, so no README edit
  is required for this gate.

Remaining terminal evidence is the Owner-operated Lightroom live exit gate.

## Stop conditions

Stop for Controller/Owner review if the fix requires changing Lightroom's authoritative renderer role, direct Catalog DB/cache writes, provider-specific API integration, non-Exposure Develop mutation, or a broader persistent background controller.

## Documentation impact

- `docs/AI_JUDGE_CONTRACT.md`: UPDATED
- `.agents/skills/exposure-judgment/SKILL.md`: UPDATED
- `.agents/skills/batch-consistency-review/SKILL.md`: UPDATED
- `docs/FOLDER_JOB_WORKFLOW.md`: UPDATED
- `docs/ARCHITECTURE.md`: UPDATED
- `docs/DECISIONS.md`: UPDATED
- `docs/CAPABILITY_MATRIX.md`: UPDATED
- `docs/VALIDATION_REGISTER.md`: UPDATED as evidence executes
- `docs/PROJECT_STATUS.md`: UPDATED
- `docs/ROADMAP.md`: UPDATED
- `README.md`: REVIEWED; update only if command-level user workflow materially changes

## Completion state

Remain ACTIVE until automated/integration evidence is green and the Owner performs the representative Lightroom live exit gate. Automated completion alone supports at most INTEGRATED for the new capability.
