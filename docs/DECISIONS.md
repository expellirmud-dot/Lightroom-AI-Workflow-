# Accepted Decisions - Lightroom AI Exposure Assist

## Approved target architecture

- The canonical target is a provider-agnostic Exposure Session composed of immutable iterative passes.
- Lightroom Classic is the authoritative renderer. The system does not replace Lightroom's preset, color, or rendering engine.
- External vision AI owns photographic/semantic judgment and writes untrusted decision JSON only.
- Deterministic Python owns preview-cache extraction, identity/schema validation, pass lineage, render freshness, convergence, bounds and deterministic planning.
- The Lightroom plug-in owns Lightroom identity capture plus explicit Prepare / Import-Apply / Prepare-Next commands.
- The durable session/pass directory is the IPC boundary between Lightroom, Python and external AI.

## WO-037 decoupling decision

The Lightroom plug-in must not remain alive waiting for AI and must not own a resident AI connection, polling loop, browser session, provider client or API credential.

Canonical command ownership is:

```text
Prepare AI Package
-> save durable pass package
-> PACKAGE_READY
-> plug-in exits

External AI Runner
-> runs later, optionally with Lightroom closed
-> reads package
-> writes decisions
-> exits

Import / Apply AI Results
-> validate/freeze exact decisions
-> guarded Exposure2012-only apply + Lightroom verification
-> SESSION_COMPLETE or RERENDER_REQUIRED
-> plug-in exits

Prepare Next AI Package
-> explicit command after rerender
-> next immutable pass
-> PACKAGE_READY
-> plug-in exits
```

A single generic Resume command is not the canonical user workflow because it mixes result import, mutation, rerender boundary and next-pass capture.

Legacy `IterativeSession.lua` / `ResumeIterativeSession.lua` may remain temporarily for compatibility, but canonical menu routing uses the explicit WO-037 commands.

## Preview-cache decision

- Lightroom plug-in supplies identity and current Catalog `Exposure2012`.
- Python, not Lua, owns `Previews.lrdata` snapshot/mapping/JPEG extraction.
- Cache access is read-only through validated snapshots.
- Python must never infer job scope from cache contents alone; the Lightroom identity handoff is authoritative for which source images belong to the pass.
- Extracted JPEG previews are Lightroom-rendered evidence for AI, not replacement renderings.

## WO-038 contact-sheet decision

- The current RootPixels JPEG extractor remains the selected source. A read-only
  forensic check of session `sess-1788131769` found only 320px JPEG payloads in
  the authorized DB snapshots; higher PyramidLevel tiers were metadata without
  accessible bytes in those snapshots.
- Python creates immutable 4×4 contact sheets and an ordered index from the
  validated extracted previews before external AI handoff. This is not an AI
  generation step.
- Contact sheets are context-first input for exposure comparison. The AI opens
  individual previews only when necessary and must not cull frames or judge
  focus/blur/sharpness/relevance from the small package images.
- Temporary cache DB snapshots are deleted only after package validation passes;
  manifest preview SHA/byte evidence and sheet/index evidence remain.

## Session and pass decisions

- Use `parent_pass_id`, not `parent_job_id`.
- Pass 1 is created only by Prepare AI Package.
- A later pass is created only by Prepare Next AI Package.
- Import / Apply AI Results never creates another pass implicitly.
- A confirmed pass is never silently re-applied.
- PASS and REVIEW are non-mutating. Only validated ADJUST may enter apply planning.

## Current iterative mutation decision

WO-037 does not redesign mutation. It reuses WO-034's Catalog-authoritative iterative safeguards:

- read current Catalog Exposure2012;
- compare it against the expected pre-apply value;
- apply only `{ Exposure2012 = target }`;
- read back the Catalog value;
- advance state only from Lightroom-observed `APPLIED_VERIFIED` evidence.

Legacy transactional XMP capabilities remain preserved outside this orchestration change and are not expanded by WO-037.

## Render decision

- A non-converged confirmed pass ends at `RERENDER_REQUIRED`.
- The next correction cannot be prepared implicitly from the apply command.
- Prepare Next AI Package is the explicit render-generation boundary.
- Python's existing render barrier must reject stale/unproven previews before the next pass advances.

## Provider decisions

- The canonical AI boundary is a filesystem pass package.
- File-capable agents, free/local vision models, AI desktop/web apps and optional API adapters may all produce the same decision contract.
- Provider/model identity is audit metadata, not authority.
- Credentials and network dependencies belong only to optional external adapters.
- No API key is required by the Lightroom plug-in or package/session core.

## Preserved decisions

- exactly one active Lightroom folder and proprietary-RAW master scope;
- no direct Catalog database access;
- no `.lrdata` writes;
- ordered identity manifests and preview byte/SHA verification;
- external AI has no mutation authority;
- only Exposure2012 is writable in the WO-037 iterative Catalog path;
- final JPEG export remains manual;
- runtime artifacts and credentials are never committed.

## Deferred decisions

WO-037 intentionally does not settle:

- AI model/provider quality;
- image batching/contact-sheet size;
- candidate/reference retrieval redesign;
- scene/group architecture redesign;
- provider-specific transport automation.

Those are independent of the Lightroom/package boundary and must be addressed in later evidence-driven work.

## Governance decisions

- Dirty paths are classified `NON_BLOCKING`, `BLOCKING`, or `CRITICAL` by material risk.
- A completed same-thread read-first preflight may be reused while authority and relevant repository fingerprints remain unchanged.
- Serena/CodeGraph are on-demand rather than mandatory preflight gates.
