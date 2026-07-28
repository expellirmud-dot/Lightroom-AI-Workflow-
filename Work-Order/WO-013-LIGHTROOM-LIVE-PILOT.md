# WO-013 — Lightroom Live Pilot

STATUS: PLANNED

## Objective

Run a bounded human-controlled pilot with Lightroom Classic and representative copies of photographs to verify the plugin handoff and dry-run workflow before any production use.

## Read-First Level

`IMPACT`

## Capability Impact

| Capability | Before | Target After |
|---|---|---|
| Lightroom selection and preview workflow | INTEGRATED | LIVE_VERIFIED |
| End-to-end dry-run workflow | INTEGRATED | LIVE_VERIFIED |
| Lightroom metadata read-back readiness | NOT_STARTED | VERIFIED_OR_BLOCKED |

## Preconditions

- WO-005 through WO-012 are closed with clean commits.
- Owner explicitly authorizes the pilot window.
- Use copied test photos and copied XMP sidecars only.
- `dry_run` remains enabled unless a later separately authorized Work Order permits real write.
- Backup and restore procedure is reviewed before execution.

## Scope

- Install/load the plug-in in Lightroom Classic.
- Select a small representative test set.
- Export Lightroom-rendered previews and verify order and naming.
- Execute the one-shot dry-run backend.
- Review manifest, decisions, proposal artifacts, result, and logs.
- Confirm no catalog, RAW, JPEG original, or source XMP mutation.
- Record exact Lightroom version, SDK behavior, commands, evidence, failures, and user observations.
- Do not enable external AI, production XMP writes, automatic rejection, deletion, or export automation.

## Validation Outcome

Record each capability as `LIVE_VERIFIED`, `BLOCKED`, or unchanged based on executed evidence. A worker report or static test alone is insufficient.

## Closeout

Update all affected canonical documents and registers. Commit evidence once if authorized. Do not push without owner instruction and do not create later work automatically.
