# WO-021: Vision Provider Integration Seam

## Objective
Implement and wire the actual Vision API capable of reading Lightroom cached previews and returning structured SinglePassDecision objects in JSON.

## Scope
- Integrate a real vision capable endpoint.
- Serialize image bytes securely.
- Enforce the single-pass prompt rules.
- Parse responses exactly to `SinglePassDecision`.
- No XMP mutation in this WO.

## Acceptance
- Provide real AI decisions against a mock job directory.
- End-to-end integration proving `analyze_job_single_pass` returns structured decisions correctly via API call without raising `NotImplementedError`.

## Status
NOT_STARTED
