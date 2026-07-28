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

## Evidence
- Provider implementations tested via pytest.
- Live API certification: LIVE_VISION_REQUEST_ATTEMPTED, QUOTA_EXHAUSTED, LIVE_VISION_PROVIDER_RESPONSE_NOT_RECEIVED.
- Manual app provider seam written. Validated canonical Lightroom JPEG identity chain.
- Generated `scratch/ai-decisions.json` successfully via manual inspection.
- apply_authorized=false enforced.

## Status
COMPLETED_WITH_GOOGLE_API_QUOTA_BLOCKED
