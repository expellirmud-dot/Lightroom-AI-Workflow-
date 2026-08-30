# WO-035 — Pause/Resume AI Handoff Workflow

STATUS: CI_CERTIFIED_LIVE_WORKFLOW_GATE_PENDING

## Goal
Complete the Lightroom iterative workflow shell without requiring a live AI provider test. A session must be able to prepare a pass, stop in a durable WAITING_FOR_AI state, and later resume the same pass after decision JSON files appear.

## Owner direction
- Skip AI model/provider quality testing for now.
- Build and certify the workflow around the AI boundary first.
- Do not require API credentials.
- Do not mutate Lightroom while decisions are missing.

## Required user workflow
1. In Lightroom, start a whole-folder iterative session.
2. Plug-in captures Catalog Exposure2012, selection identity, preview cache snapshot, previews, manifest, schema, and AI task.
3. Plug-in stops cleanly and reports WAITING_FOR_AI. No AI invocation and no Catalog mutation occurs in this command.
4. An external AI app may later place one decision JSON per FOUND preview into the prepared `decisions` directory.
5. User invokes Resume Pending Iterative Session.
6. Resume validates that every required decision file exists before invoking Python analysis validation.
7. If decisions are incomplete, Resume returns to WAITING_FOR_AI without error and without mutation.
8. If decisions are complete, Resume validates/freeze-imports them, builds the Catalog apply plan, applies only Exposure2012, and confirms Lightroom-observed results.
9. If another pass is needed, the workflow stops at WAITING_FOR_RERENDER. A later Resume prepares the next pass and pauses again at WAITING_FOR_AI.

## Safety / lineage requirements
- Resume uses `runtime/staging/latest-session.json`; it must not silently start a new session.
- Active Lightroom folder on Resume must match the persisted session source root.
- Missing or malformed session/pass artifacts fail closed.
- Missing decisions are a normal WAITING_FOR_AI state, not a fatal error.
- Analyze runs at most once for a prepared pass; an existing frozen `ai-decisions.json` is reused.
- An existing Catalog apply plan/result/evidence is reused rather than blindly repeating mutation.
- A confirmed pass is never re-applied; the next Resume becomes the explicit rerender boundary before preparing another pass.
- Catalog apply remains absolute-target, drift-checked, Exposure2012-only.
- No XMP Save Metadata / Read Metadata dependency is introduced.

## Non-goals
- No live AI provider call.
- No AI quality benchmark.
- No scene grouping redesign.
- No prompt/model selection work.
- No automatic background monitoring of the decisions directory.

## Automated acceptance
- Lightroom menu exposes Prepare Whole-Folder Iterative Session and Resume Pending Iterative Session.
- Start command does not invoke `--analyze-session-pass` or apply logic.
- Start creates Pass 1 then stops at WAITING_FOR_AI.
- Resume checks decision completeness before analysis.
- Missing decision files cause a clean WAITING_FOR_AI path.
- Resume uses the existing session/pass IDs and verifies the active folder identity.
- Successful Resume can analyze/freeze, plan, Catalog-apply, and confirm.
- A non-converged confirmed pass stops at WAITING_FOR_RERENDER; a later Resume prepares the next pass and returns to WAITING_FOR_AI.
- Existing WO-034 Catalog-authoritative safeguards remain intact.
- Full Windows CI passes on Python 3.12 and 3.13.

## Automated validation result
- GitHub Actions run: `33328089473` (`Lightroom AI Workflow Certification`, run 75).
- Windows / Python 3.12: PASS — focused prepared-job tests, full pytest suite, config smoke test, integration suite, compile check, diff check, clean-tree check.
- Windows / Python 3.13: PASS — same certification gates.
- No live AI provider was invoked by this certification.

## Live gate
A later Lightroom test only needs to prove workflow mechanics with manually supplied decision JSON. AI model/provider correctness is explicitly deferred.
