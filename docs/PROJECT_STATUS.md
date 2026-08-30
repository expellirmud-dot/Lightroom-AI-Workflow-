# Project Status

LAST_UPDATED: 2026-08-30
PROJECT_PHASE: Diagnostic-First Implementation
CURRENT_WORK_ORDER: Work-Order/WO-031-DIAGNOSE-CURRENT-FOLDER.md
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-030-EXPOSURE-SESSION-DOCUMENTATION.md
CURRENT_BRANCH: main
PR_1_STATUS: MERGED_ON_2026-08-13

> Moving Git HEAD is intentionally not duplicated in this document. Git is the
> authority for the current commit; this file records project phase and evidence
> boundaries so a documentation commit does not make its own HEAD field stale.

## Current implementation truth

The code and Lightroom plug-in currently implement WO-029's prepared-folder
single-pass workflow:

```text
Prepare Current Folder
-> external file decisions
-> Apply Prepared Job
```

Automated Windows evidence covers the Python prepared-job lifecycle, strict
decision import, and transactional XMP paths. It does not prove the approved
iterative Exposure Session target.

The owner verified Lightroom plug-in version 1.1.0 build 2 loads and both menu
commands appear. The first real **Prepare Current Folder** attempt failed inside
Lua eligibility filtering with zero eligible proprietary-RAW masters. Because
that failure occurred before staging/CLI/cache execution, current runtime
evidence does not identify direct photo count or the actual Lightroom
`fileFormat` values.

WO-029 is `SUPERSEDED`, not completed or live verified. WO-030 reconciled the
canonical target architecture and governance. WO-031 is now authorized only for
the diagnostic-first seam.

## Approved target

The accepted architecture remains:

```text
provider-agnostic Exposure Session
-> immutable iterative passes
-> Lightroom authoritative rendering
-> external vision scene/group/outlier judgment
-> deterministic Python validation/convergence/XMP safety
-> thin Lightroom coordination
```

It includes diagnostic-first preflight, PASS/ADJUST/REVIEW, persistent scene
groups with safe split/REVIEW, render-generation proof, metadata-sync safety,
convergence/oscillation controls, and bounded safe stop. Session/pass
capabilities remain `PLANNED`; WO-031 does not authorize them.

## Current authorized seam

Implement `DIAGNOSE_CURRENT_FOLDER` as one read-only aggregated diagnostic run.
It must continue independent checks even when eligible RAW count is zero and
produce machine-readable plus human-readable evidence covering active-folder
metadata, eligibility, preview-cache readiness, runtime/CLI/bridge readiness,
and safe XMP-readiness checks where independently testable.

The purpose is to replace the current one-error-at-a-time Lightroom debugging
loop with one evidence-rich owner test.

## Preserved evidence and safety

- Historical selected-photo cache extraction remains evidence, not a target
  workflow.
- Read-only SQLite cache snapshot/extraction is preserved.
- Transactional XMP backup, hash verification, atomic replacement,
  post-write validation, rollback, and checkpoint behavior remain preserved.
- Only `crs:Exposure2012` is in writable scope for future authorized apply;
  WO-031 itself is read-only.
- Final JPEG export remains manual.

## Current risks

- Active-folder eligibility has not yet been diagnosed at runtime.
- Current code has no session/pass lineage, rerender freshness barrier,
  convergence, oscillation detection, or metadata synchronization proof.
- Optional legacy Google/API compatibility remains outside the canonical target
  and is not part of WO-031.
- Real XMP apply and Lightroom metadata/render round-trip remain unverified.

## Next gate

Complete WO-031 automated validation, then perform exactly one bounded real
Lightroom `DIAGNOSE_CURRENT_FOLDER` run. Use that artifact to decide the next
implementation seam; do not start session/pass work before this gate.
