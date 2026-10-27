# RCV-001 — Read-only photographic acceptance evidence gate

**State:** DONE — narrowly bounded **read-only audit scope** (NOT photographic acceptance, NOT production release)  
**Date:** 2026-10-27, Asia/Bangkok  
**Owner request:** roadmap → bounded Work Order → review code → test → commit/push → begin next task  
**Branch:** `recovery/photo-exposure-validation-20261027`, based on `17491925a522`. Separate from local active WO-057 release work.  
**Owner/Controller:** ChatGPT Controller; no delegated worker; local source/tests reviewed read-only.

## Goal

Prevent a replay of the 2026-10-09 24-photo failure being confused with a passed photographic gate: AI said `KEEP 24/24` while an independent full-size review flagged three opposing directions. All evidence must be reported as advisory. **Do not write or adjust any real photograph.**

## Authorized scope

- Read local `CURRENT_WORK_ORDER`, `AGENTS.md`, `START_HERE.md`, targeted source modules and frozen validation JSON; preserve owner files.
- New **standalone read-only** `tools/photographic_gate_audit.py` and `tests/test_photographic_gate_audit.py`.
- Recovery planning documentation only in `docs/recovery/`; no `main` merge and no active Work Order pointer change.
- Test/compile in existing ignored `runtime/temp/rcv001-20261027/` copy, not inside dirty tracked source.
- No modifying Git `.git/index.lock`, no Git reset/clean/stash/add/commit on the dirty checkout, and no real Lightroom/Catalog/XMP/RAW/JPEG write.

## Acceptance / DONE criteria

- [x] Correctly classify the frozen 24-photo result as **BLOCKED** (not `COMPLETE`).
- [x] Cross-reference all three strong flagged image identities and exposure directions with the independent review.
- [x] Reject missing/invalid worker count totals and changed photo identities.
- [x] Treat absent photographer acceptance as blocked; no inferred numeric EV or Lightroom mutation authority.
- [x] Run focused unit tests and real evidence replay locally, record observed result.
- [x] Manual code review for safety and portability; verify remote branch file contents after commit.
- [ ] Actual photographic quality acceptance — **NOT IN SCOPE**; remains blocked.
- [ ] Actual Lightroom Before/After render and User/Owner photographic target approval — **NOT IN SCOPE**; RCV-002/R3.

## Executed evidence and code review

1. Existing project tests: `test_reference_free_target_planning.py`, `test_production_scene_measurement.py`, `test_production_multiface_measurement.py`, `test_scene_histogram.py`: **15 passed** (4.92 sec; Python project venv). This is a technical baseline, NOT photo quality.
2. New isolated audit suite: `python -m unittest discover -s tests -p test_photographic_gate_audit.py -v`: **5/5 PASS**. Refactored test import to locate the sibling `tools/` directory in a clean tree; confirmed rerun.
3. Isolated `python -m compileall -q tools tests`: exit 0; `pytest -q -p no:cacheprovider --basetemp=...`: **5/5 PASS** (2.08 sec).
4. Real historical `final-result.json` + `fullsize-review-progress.json` replay: audit returned **`BLOCKED_PHOTOGRAPHIC_PROMOTION`**. Sample 24, KEEP 24, 11 full-size review items, exact three verified review-direction disagreements: `PTO_9197 DARKEN`, `PTO_9271 DARKEN`, `PTO_9419 BRIGHTEN`. Reasons: `ALL_KEEP_CONTRADICTS_INDEPENDENT_REVIEW`, `PHOTOGRAPHER_ACCEPTANCE_MISSING`. CLI intentional blocked exit 2; harness correctly accepted that as expected *rejection*, not photo success.
5. **Manual code review:** the new tool reads only two JSON inputs and emits a JSON summary; no file or Lightroom mutations. It validates count totals, unique review indices, identity and review-direction matching; the output explicitly says photographic quality is **not** certified. Initial test import layout flaw was corrected before remote code commit. Audit has no ability to provide automatic EV targets.
6. **Review limitation:** Only 11 photos were independently reviewed at full size, the review labels are provisional, and this small script does **not** validate current JPEG hash bytes or execute any renderer. It cannot establish a true-photo positive/negative/zero ground truth or resolve photographic method accuracy.

## Commits and delivery

- Roadmap: `83419fb39549a518cdaa2b77cbde38567c903a24`.
- Test-only audit: `effdabdc597da84854ba114099f86f9db8819350`.
- Five regression tests: `6556e18c4a0973ae3c794a4e7f63c47ef34cc319`.
- Files are committed directly to the **GitHub recovery branch** using the authorized GitHub connector, and source/test file retrieval from that remote branch was verified. This is remote delivery equivalent to committing/pushing a branch; the dirty Windows checkout and origin/main were not touched.

## STOP conditions and next action

- The RCV-001 **quality rejection** gate is DONE; product correction is **not** done.
- RCV-002 begins with read-only diagnosis of the existing target generation + renderer calibration seam. It must investigate real Lightroom response to exposure without assuming synthetic JPEG brackets are actual RAW rendering.
- No numeric EV auto-authority, no Catalog/XMP edit, no GUI input, no expensive full-album rerun before Owner-controlled photo proof.
- If the branch is integrated into main later, complete existing blocked WO-057 clean-checkout dependency closure first.

## Local evidence references (private, NOT committed)

- `runtime/jobs/20261006-2569-09-02/phase3-exposure/validation/bounded-24-exposure-speed-20261009/final-result.json`
- `runtime/jobs/20261006-2569-09-02/phase3-exposure/validation/bounded-24-exposure-speed-20261009/fullsize-review-progress.json`
- `runtime/temp/rcv001-20261027/`: isolated exact source/test copy and runtime proof; disposable only after future exact-scope authorized cleanup.
