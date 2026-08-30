# Project Status

LAST_UPDATED: 2026-08-30
PROJECT_PHASE: Exposure Session Target Documented - Implementation Not Authorized
CURRENT_WORK_ORDER: NONE
LATEST_COMPLETED_WORK_ORDER: Work-Order/WO-030-EXPOSURE-SESSION-DOCUMENTATION.md
CURRENT_BRANCH: main
CURRENT_HEAD: 68a020a313ab1e0ea6fcf7f7bc6da9f907ee713c
PR_1_STATUS: MERGED_ON_2026-08-13

## Current implementation truth

The code and Lightroom plug-in on `main` implement WO-029's prepared-folder
single-pass workflow:

```text
Prepare Current Folder
-> external file decisions
-> Apply Prepared Job
```

Automated Windows evidence covers the Python prepared-job lifecycle, strict
decision import, and transactional XMP paths. It does not prove the approved
iterative Exposure Session target.

The owner verified that Lightroom plug-in version 1.1.0 build 2 loads and both
menu commands appear. The first real **Prepare Current Folder** attempt failed
inside Lua eligibility filtering with zero eligible proprietary-RAW masters.
Because failure occurred before staging/CLI/cache execution, current runtime
evidence does not identify direct photo count or observed Lightroom
`fileFormat` values.

WO-029 is `SUPERSEDED`, not completed or live verified.

## Approved target

The accepted architecture is:

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
convergence/oscillation controls, and bounded safe stop. These capabilities are
`PLANNED`; documentation approval is not implementation evidence.

## Preserved evidence and safety

- A historical real selected-photo path reached cache extraction and external
  decision import without XMP mutation under WO-028.
- Read-only SQLite cache snapshot/extraction is automated and historically
  live proven for one selected photo.
- Transactional XMP backup, SHA-256 verification, atomic replacement,
  post-write validation, rollback, and checkpoint behavior have automated
  evidence.
- Only `crs:Exposure2012` is in writable scope; final export remains manual.

## Current risks

- Active-folder eligibility is not diagnosed at runtime and currently fails
  with one generic zero-eligible error.
- Current code has no session/pass lineage, rerender freshness barrier,
  convergence, oscillation detection, or metadata synchronization proof.
- The current optional Google/API compatibility dependency remains in source
  and packaging even though it is not the canonical target.
- Real XMP apply and Lightroom metadata/render round-trip remain unverified.

## Next implementation seam

After owner approval and a separate bounded implementation Work Order, build
`DIAGNOSE_CURRENT_FOLDER` first. It must aggregate active-folder metadata,
eligibility, preview-cache, runtime/CLI/bridge, and XMP-readiness evidence in
one read-only run before any session/pass or real apply implementation begins.
