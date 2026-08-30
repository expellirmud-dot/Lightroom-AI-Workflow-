# WO-036 — Lightroom Live-Test Harness

STATUS: COMPLETE_CI_CERTIFIED

## Goal
Remove avoidable manual setup from the remaining Lightroom Classic live gate without testing any AI model/provider.

## Scope
- Add a deterministic decision seeder for the currently prepared WO-035 pass.
- `pass-all` writes valid PASS decisions for every FOUND preview and never requests a Lightroom mutation.
- `one-adjust` writes exactly one small ADJUST decision for the first FOUND preview and PASS for all remaining FOUND previews.
- Default live adjustment is +0.10 EV and the utility refuses absolute test deltas above 0.25 EV.
- Refuse to overwrite existing decision files unless `--force` is explicit.
- Refuse any pass that already has frozen AI decisions or Catalog apply evidence.
- Do not call AI, edit RAW/XMP, or touch the Lightroom Catalog.

## Intended live sequence at closeout
1. Lightroom: prepare the iterative pass.
2. Seed deterministic decisions using the WO-036 utility.
3. Lightroom: process the seeded results.
4. For the bounded mutation proof, use a fresh test session/pass with `one-adjust --delta-ev 0.10`.
5. Verify exactly one intended image changes Exposure2012 by +0.10 EV and no other Develop setting changes.

The user-facing command/state names above are superseded by WO-037's decoupled package workflow; the deterministic seeder remains valid as a no-AI test utility.

## Acceptance
- Seeder generates exact manifest-ID decision coverage.
- PASS mode generates zero delta for all entries.
- one-adjust changes exactly one decision.
- Frozen/applied passes fail closed.
- Existing decisions are not overwritten implicitly.
- Automated Windows CI remains green on Python 3.12 and 3.13.

## Validation evidence
- Merged to `main` in commit `a316adf050429ddaf94554a5410cd7299262c5cd`.
- Post-merge GitHub Actions run #80 (`Lightroom AI Workflow Certification`) completed successfully on 2026-08-30.

## Remaining live evidence
The actual Lightroom Classic live mutation/rerender proof remains pending. WO-037 changes only the orchestration boundary before that live gate; it does not claim live verification.

## Non-goals
- AI quality or provider testing.
- Scene/reference redesign.
- Automatic AI transport.
- Replacing the actual Lightroom Classic live gate.
