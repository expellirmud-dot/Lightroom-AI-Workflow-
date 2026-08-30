# WO-035 — Pause/Resume AI Handoff Workflow

STATUS: IN_PROGRESS

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
8. If decisions are complete, Resume validates/freeze-imports them, builds the Catalog apply plan, applies only Exposure2012, confirms Lightroom-observed results, and either completes or prepares the next pass.
9. If another pass is needed, the next pass is prepared and the workflow pauses again in WAITING_FOR_AI.

## Safety / lineage requirements
- Resume uses `runtime/staging/latest-session.json`; it must not silently start a new session.
- Active Lightroom folder on Resume must match the persisted session source root.
- Missing or malformed session/pass artifacts fail closed.
- Missing decisions are a normal WAITING_FOR_AI state, not a fatal error.
- Analyze runs at most once for a prepared pass and apply consumes the frozen `ai-decisions.json`.
- Catalog apply remains absolute-target, drift-checked, Exposure2012-only.
- No XMP Save Metadata / Read Metadata dependency is introduced.

## Non-goals
- No live AI provider call.
- No AI quality benchmark.
- No scene grouping redesign.
- No prompt/model selection work.
- No automatic background monitoring of the decisions directory.

## Automated acceptance
- Lightroom menu exposes Start/Prepare and Resume commands.
- Start command does not invoke `--analyze-session-pass` or apply logic.
- Start creates Pass 1 then stops at WAITING_FOR_AI.
- Resume checks decision completeness before analysis.
- Missing decision files cause a clean WAITING_FOR_AI path.
- Resume uses the existing session/pass IDs and verifies the active folder identity.
- Successful Resume can analyze/freeze, plan, Catalog-apply, confirm, and prepare the next pass.
- Next pass pauses again instead of immediately invoking AI.
- Existing WO-034 Catalog-authoritative safeguards remain intact.
- Full Windows CI passes on Python 3.12 and 3.13.

## Live gate
A later Lightroom test only needs to prove workflow mechanics with manually supplied decision JSON. AI model/provider correctness is explicitly deferred.
