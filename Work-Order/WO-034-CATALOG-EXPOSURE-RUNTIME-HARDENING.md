# WO-034 — Catalog Exposure Runtime Hardening

STATUS: IN_PROGRESS

## Goal
Finish the Lightroom iterative-session runtime boundary before any new Vision architecture work. The iterative path must use the Lightroom Catalog as the authoritative Exposure2012 state and must never re-run AI during apply.

## Current defects this WO closes
1. `apply_session_pass()` re-runs `analyze_job_single_pass()` instead of consuming the frozen analysis artifact.
2. Session exposure math starts from `0.0` instead of the real Catalog Exposure2012 baseline.
3. Policy declares 0.05 EV quantization but convergence does not apply it.
4. Current pass numbering is derived incorrectly after the pass has already been appended.
5. Iterative apply still writes XMP externally and calls Lightroom `readMetadata()`.
6. Iterative render freshness is tied to XMP instead of the Catalog Develop state.

## Authority and scope
- Scope is the whole-folder iterative session only.
- Legacy prepared-job/single-pass XMP workflow remains available for backward compatibility.
- Lightroom Catalog is authoritative for iterative `Exposure2012`.
- Iterative mutation may change only `Exposure2012` through Lightroom SDK `applyDevelopSettings`.
- AI analysis runs once per pass. Apply consumes persisted `ai-decisions.json` only.
- XMP metadata synchronization is not a prerequisite for the Catalog iterative route.

## Required implementation
### A. Catalog baseline
- Lightroom selection payload includes current Catalog `Exposure2012` from `getDevelopSettings()`.
- Session persists `baseline_exposure2012` and initializes `expected_exposure2012` from it.

### B. Frozen decision apply
- Analyze writes immutable `ai-decisions.json`.
- Apply planning loads and validates that file; no provider invocation is allowed in apply planning or confirmation.

### C. Quantized convergence
- Apply configured EV quantization before bounds/history calculations.
- Resolve pass number from the actual `pass_id` already present in session lineage.

### D. Two-phase Catalog mutation
1. Python creates `catalog-apply-plan.json` with absolute `expected_before_exposure2012` and `target_exposure2012` per approved image.
2. Lightroom re-reads Catalog develop state immediately before mutation.
3. Drift from expected-before fails closed for that image.
4. Lightroom applies only `{ Exposure2012 = target }` inside catalog write access and verifies observed-after.
5. Lightroom writes `catalog-apply-result.json`.
6. Python confirms the result and only then commits session history/state.

### E. Render freshness
For a previously adjusted image, the next pass is valid only when:
- current Catalog Exposure2012 equals the session expected value; and
- a valid refreshed preview exists; and
- preview hash differs from the pre-apply preview hash.
No XMP comparison is used for the iterative Catalog route.

## Automated acceptance
- Non-zero Catalog baseline is preserved in target math.
- 0.05 EV quantization is exercised by tests.
- Apply planning never calls the AI provider.
- Lightroom iterative plugin contains `getDevelopSettings` and `applyDevelopSettings` and does not call `readMetadata`.
- Catalog drift produces fail-closed result.
- Confirmation records only Lightroom-verified applies.
- Existing legacy prepared-job tests remain green.
- Full Windows CI passes on Python 3.12 and 3.13.

## Live acceptance gate
CI cannot host Lightroom Classic. After automated certification, owner performs a bounded 1–3 image Lightroom test confirming:
1. baseline Exposure2012 read from Catalog;
2. only Exposure2012 changes;
3. target is absolute and correct;
4. fresh Lightroom preview is observed on the next pass;
5. no XMP Save/Read Metadata ritual is required.

## Non-goals
- No new scene/retrieval architecture.
- No new Vision model/provider selection.
- No LUMINA metering port.
- No UI redesign beyond messages required by this runtime boundary.
