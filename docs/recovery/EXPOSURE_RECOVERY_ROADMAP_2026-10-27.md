# Exposure recovery roadmap — 2026-10-27

> **Release status:** recovery branch / proposed plan; not a merge to `main`, and not a replacement for the locally active WO-057. The working tree on Windows contains 196 dirty/untracked paths and a historical `.git/index.lock`. Do not reset, stash, delete the lock, or bulk stage. Remote `main` is an outdated September snapshot; this branch is an isolated planning/test delivery.

## Product goal

Make the existing Lightroom Classic Exposure assistant reliably correct **in actual rendered photographs**, not merely green in schema/unit tests. Keep Nikon NEF originals, Lightroom Catalog, cache, and all unrelated Develop settings safe. Prioritize the Owner-selected baseline **Import + preset + verified Lightroom Standard Preview/contact sheet**. No automatic XMP/Catalog mutation during this recovery until separately approved.

## Evidence already established (local, 2026-10-27, read-only)

- Local repository: `D:\ai-tools\lightroom-ai-exposure`; HEAD `17491925a522`, branch `main`; 196 modified/untracked paths. An old zero-byte index lock dated 2026-09-11 exists. No running `git.exe` was seen at the preflight; lock has **not** been removed.
- Local active Work Order: WO-057 G0 release baseline BLOCKED; WO-053 photographic method PAUSED. The first recovery delivery must not merge mixed-generation files or pretend the current GitHub `main` includes the uncommitted offline workflow.
- Existing 2026-10-09 real 1,005-image package: 1,005/1,005 verified previews, 63/63 sheets; **infrastructure success only**, no photographic acceptance.
- Bounded 24-image experiment: Gemini Flash Lite output KEEP 24/24 while independent review flagged `PTO_9197` and `PTO_9271` as potentially too bright and `PTO_9419` as potentially too dark. These are **review candidates**, not photographer-approved numeric EV truth.
- Known 752-image historical failure: `PTO_8855.NEF` was accepted numerically after 0 → +1.00 → +1.25 EV but the rendered subject/highlights looked washed out. Do not repeat scene-median-as-photo-quality acceptance.
- In the current dirty local source, `reference_free_target.py` explicitly generates **synthetic display-JPEG brackets**, not actual Lightroom Exposure2012 renders. `scene_measurement.py` exposes display-domain histogram evidence, not photographic target authority. `production_job.py` uses YOLO/skin ROI median for reference-free jobs. None of those outputs alone proves suitable exposure.
- 2026-10-27 smoke run of existing focused tests: 15 passed, exit 0, from reference-free, production scene/multiface and histogram test modules. **No live renderer or photographic test was run.**

## Roadmap — staged with pass/fail gates

| Gate | Scope and deliverable | Definition of DONE / exit |
|---|---|---|
| **R0: Repository safety and failure inventory** | Read-only current local source/authority + exact failure evidence; review exposure-path assumptions; targeted smoke | Written evidence map; safe branch; known legacy defects and quality blockers identified; untouched owner files. Does not claim photo quality. |
| **R1: Photographer-anchored regression gate** | Frozen subset of real preset-applied previews: DARKEN, KEEP, BRIGHTEN, backlit/mixed light. Exact identities and hashes; provisional review vs Owner-approved truth explicitly separated. Read-only audit utility/tests. | Audit rejects known KEEP-24/24 false success and missing Owner truth; report includes complete counts, uncertainty and source evidence. Candidate images preserved. |
| **R2: Correct decision method, bounded** | Evaluate 2–3 genuinely different hypotheses, no automatic change based solely on histograms/skin L*; compare visual quality and latency; one narrow reversible source change at a time | Positive/zero/negative controls pass independent review **on previously unseen images**; no false KEEP for known cases; no regression on good controls. |
| **R3: Real Lightroom renderer closure** | Same NEF + unchanged preset/profile/WB, targeted Lightroom Exposure2012 candidates, fresh Standard Previews, exact image hash + Catalog state | Verified Before/After Lightroom renders; correct direction **and** acceptable subject/highlight retention; no synthetic JPEG substitutions; Owner accepts results. |
| **R4: Batch reliability** | Representative 20 → 50 → larger album, only after R3. Exact identity, rerender freshness, bounded retry, no invisible skipping, timings | Every input accounted `ADJUSTED + NO_CHANGE + UNRESOLVED = N`; unresolved are explicit; measured latency and recheck success; safe stop on drift. |
| **R5: Release** | Review, clean checkout, bounded end-to-end tests, secret scan, change review, commit/push exact closure with rollback | Reviewer-approved implementation, verified clean checkout + Lightroom human acceptance; no accidental publication of the 196-path dirty workspace; explicit Owner authority for real writes. |

## Time-box and priorities

Owner states deadline **20:00 Asia/Bangkok, 2026-10-27** and requests tangible progress rather than more architecture speculation. The bounded first deliverable is **R0 + executable R1 quality rejection test**, not a claim of fully working album exposure. If evidence is insufficient, stop and report exact blocker rather than broadening scope.

## Safety and Git delivery contract

1. Record current local HEAD/status and do **not** edit/stage its inherited dirty files.
2. For first delivery, use separate `recovery/photo-exposure-validation-20261027` remote branch created from `17491925a522`. Scope files exclusively under `docs/recovery/` and new stand-alone test-only audit tool/test; no merge to `main`.
3. Review exact code and test intended failure paths before writing. Unit tests are necessary but not photographic acceptance.
4. Verify file bytes, test output, GitHub commit SHAs and remote file retrieval. A GitHub API file commit is already on the remote branch; it is **not** a claim that the local dirty checkout ran `git push`.
5. Never treat a review candidate as camera-RAW clipping proof or photographer ground truth; display JPEG highlights are only observational evidence.
6. No live Lightroom GUI control, Catalog/XMP mutation, RAW move/delete, or secrets involved.

## Immediate next Work Order

**RCV-001 — Read-only exposure photographic quality gate** in this branch. After test-only validation, **RCV-002** begins by tracing and ranking the actual deterministic target mapping/failure mode using the smallest complete read set and the known 24-image evidence. RCV-002 cannot promote code based solely on a model verdict.
