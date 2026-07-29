# AI Judge Contract — External File Workflow

## Input

The AI receives one prepared job folder containing `AI_TASK.md`,
`manifest.json`, `decision-schema.json`, and Lightroom-rendered JPEG previews.
Only manifest entries with `extraction_status: FOUND` require decisions.

The AI may be any local or connected vision-capable application. No network API
provider is required by the Lightroom application.

## Required judgment

The AI must apply the repository skills for exposure, batch consistency,
relevance, and visual quality. It must inspect the actual preview bytes and not
infer decisions from filenames.

## Decision file

Write one UTF-8 JSON object per FOUND image to
`runtime/jobs/<job-id>/decisions/<image_id>.json`:

```json
{
  "image_id": "4042206",
  "relevance_verdict": "KEEP",
  "quality_verdict": "KEEP",
  "delta_ev": 0.25,
  "confidence": 0.92,
  "highlight_risk": false,
  "shadow_risk": false,
  "subject_rationale": "The primary face is slightly dark but retains detail.",
  "scene_rationale": "Indoor event lighting should remain warm and believable.",
  "batch_consistency_group": "indoor-stage-01",
  "reason": "A modest positive correction matches the reference frames."
}
```

## Validation

- Exactly one response must exist for every FOUND manifest ID.
- Unknown, duplicate, missing, malformed, or escaping response files reject the
  batch before partial processing.
- `image_id` must match the manifest exactly.
- Extra fields are rejected.
- `delta_ev` must be finite and within configured bounds.
- `confidence` must be within `[0, 1]`.
- Low confidence or any risk flag downgrades automatic action to REVIEW.
- Manifest order is preserved in canonical analysis artifacts.
- Preview byte count and SHA-256 are verified before importing each response.

The AI never writes RAW, XMP, catalog, cache, or manifest files.
