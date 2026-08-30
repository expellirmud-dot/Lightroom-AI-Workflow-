# Project Status

LAST_UPDATED: 2026-08-31
PROJECT_PHASE: Lightroom Live Verification Pending
CURRENT_WORK_ORDER: NONE
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-037-DECOUPLED-AI-PACKAGE-WORKFLOW.md
CURRENT_BRANCH: main after PR #5 merge; Git remains authority for moving HEAD

## Current implementation truth

The automated-tested iterative session runtime now has an explicit decoupled package workflow:

```text
Prepare AI Package
-> Python read-only Lightroom preview-cache extraction
-> PACKAGE_READY
-> plug-in exits

External AI Runner
-> runs separately against the saved package
-> writes decisions only

Import / Apply AI Results
-> exact decision validation
-> guarded Catalog Exposure2012-only apply and observed confirmation
-> SESSION_COMPLETE or RERENDER_REQUIRED
-> plug-in exits

Prepare Next AI Package
-> explicit command after rerender
-> existing render barrier
-> next immutable package
-> PACKAGE_READY
```

The Lightroom plug-in does not own a resident AI listener, polling loop, provider session, browser automation or API key.

## WO-037 implementation

WO-037 adds:

- `PrepareAIPackage.lua` — Pass 1 identity/capture/package command;
- `ImportApplyAIResults.lua` — explicit result import/apply command;
- `PrepareNextAIPackage.lua` — explicit later-pass capture command;
- `SessionPackageSupport.lua` — shared Lightroom identity/selection/Exposure2012 apply helpers;
- canonical `Info.lua` routing to the new commands while retaining WO-029 single-pass commands as Legacy;
- static regressions protecting command separation, no resident listener and Exposure2012-only Catalog mutation;
- architecture/workflow/decision/user documentation aligned to the durable filesystem package boundary.

The historical `IterativeSession.lua` / `ResumeIterativeSession.lua` files remain for compatibility but are not registered as the canonical menu workflow.

The plug-in metadata remains version 1.2.0 build 1 so it stays aligned with the existing diagnostic payload contract; WO-037 changes routing rather than the diagnostic protocol.

## Automated evidence

- WO-036 post-merge run #80 succeeded on `main`.
- WO-037 PR #5 certification run #85 (`33340357782`) succeeded on Windows Python 3.12 and 3.13.
- Both matrix jobs passed focused prepared-job regressions, the full pytest suite, CLI config smoke, integration suite, compile, diff check and clean working-tree/private-artifact check.
- The first WO-037 PR run failed only because old static tests still required the superseded Resume menu/version assumptions; those contracts were updated and the subsequent run passed.

This supports CI certification/integration only. It does not prove the new Lua command routing inside a real Lightroom Classic host.

## Safety preserved

- no direct `.lrcat`, `.lrcat-wal` or `.lrcat-shm` access;
- no `.lrdata` writes;
- Python remains the read-only cache snapshot/extractor;
- external AI has decision-only authority;
- only Catalog Exposure2012 is writable through the canonical iterative apply path;
- Import / Apply never prepares another pass implicitly;
- next-pass capture remains gated by prior verified apply evidence and the existing Python render barrier;
- AI provider/model quality testing remains deferred.

## Next gate

Perform one bounded Lightroom Classic live test using the new explicit commands and the existing WO-036 deterministic no-AI decision seeder:

```text
Prepare AI Package
-> seed PASS-only or one +0.10 EV test decision set
-> Import / Apply AI Results
-> verify Lightroom-observed result
-> allow rerender
-> Prepare Next AI Package only if a second-pass proof is required
```

Do not claim `LIVE_VERIFIED` until that Lightroom-hosted evidence is captured.
