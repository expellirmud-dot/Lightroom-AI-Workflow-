# Project Status

LAST_UPDATED: 2026-08-31
PROJECT_PHASE: Decoupled AI Package Workflow Implementation
CURRENT_WORK_ORDER: Work-Order/WO-037-DECOUPLED-AI-PACKAGE-WORKFLOW.md
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-036-LIGHTROOM-LIVE-TEST-HARNESS.md
CURRENT_BRANCH: wo-037-decoupled-ai-package-workflow

> Git is the authority for moving HEAD. This file records phase and evidence boundaries only.

## Current implementation truth

Main already contains automated-tested iterative session work through WO-036, including:

- active-folder identity capture;
- Catalog Exposure2012 baseline capture;
- read-only preview-cache snapshot/extraction;
- immutable pass/session artifacts;
- external decision-file validation;
- bounded Catalog Exposure2012 apply planning and observed verification;
- deterministic no-AI live-test decision seeding.

WO-036 post-merge GitHub Actions run #80 completed successfully. Representative Lightroom Classic end-to-end mutation/rerender evidence remains pending.

## WO-037 objective

Replace the user-facing generic wait/resume semantics with three explicit short-lived Lightroom commands:

```text
Prepare AI Package
-> PACKAGE_READY
-> plug-in exits

Import / Apply AI Results
-> SESSION_COMPLETE or RERENDER_REQUIRED
-> plug-in exits

Prepare Next AI Package
-> PACKAGE_READY
-> plug-in exits
```

External AI runs independently against the saved pass directory. The Lightroom plug-in never polls or keeps an AI/provider connection alive.

## Current branch implementation

WO-037 currently adds:

- `PrepareAIPackage.lua` — Pass 1 capture/package command;
- `ImportApplyAIResults.lua` — explicit result import/apply command;
- `PrepareNextAIPackage.lua` — explicit later-pass capture command;
- `SessionPackageSupport.lua` — shared Lightroom identity/selection/apply helpers;
- plug-in menu version 1.3.0 routing to the new canonical commands;
- static regression tests for command separation and Exposure2012-only mutation;
- canonical architecture/workflow/decision/user documentation updates.

The older `IterativeSession.lua` / `ResumeIterativeSession.lua` remain in the repository for compatibility but are no longer registered as the canonical menu path.

## Safety preserved

- no direct `.lrcat` database access;
- no `.lrdata` writes;
- Python remains the cache extractor;
- external AI has decision-only authority;
- only Catalog Exposure2012 is writable through the WO-037 iterative command path;
- Import / Apply does not prepare another pass;
- next-pass capture remains gated by prior apply evidence and the existing Python render barrier.

## Evidence boundary

WO-037 is `IMPLEMENTED_PENDING_CI` on its feature branch. No claim is made yet that its new Lua command routing is Lightroom-hosted or live verified.

## Next gate

1. Run repository CI on the WO-037 pull request.
2. Repair any focused/static/Windows failures without widening architecture scope.
3. After CI is green, merge if the Work Order closeout diff remains bounded.
4. Then perform the previously deferred Lightroom Classic live package/apply/rerender test using the new explicit commands.
