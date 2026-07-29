# AI Judge Contract — External File Workflow

## Input

The AI receives one self-contained prepared job folder containing:

- `AI_TASK.md` — exact operating instructions for this job;
- `AI_SKILLS.md` — the complete bundled contents of all four canonical visual skills, including references and examples;
- `manifest.json` — ordered Lightroom identity and preview records;
- `decision-schema.json` — strict output schema;
- Lightroom-rendered JPEG previews.

Only manifest entries with `extraction_status: FOUND` require decisions. The AI may be any local or connected vision-capable application. No network API provider is required by the Lightroom application, and the AI does not need separate repository access.

## Required judgment

The AI must read `AI_SKILLS.md` completely and apply its exposure, batch consistency, relevance, and visual-quality rules. It must inspect the actual preview bytes and must not infer decisions from filenames alone.

The judgment covers intended subject/person priority, subject and background exposure, scene intent, highlight/shadow safety, focus, blur, obstruction, accidental/test-shot evidence, relevance, duplicate/supporting value, visual grouping, reference-frame choice, batch consistency, bounded EV correction, and KEEP/REVIEW/SKIP disposition.

## Decision file

Write one UTF-8 JSON object per FOUND image to `runtime/jobs/<job-id>/decisions/<image_id>.json`:

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

Use `delta_ev: 0.0` when no exposure correction is justified. Do not invent precision, objects, scene details, identities, or paths.

## Validation

- Exactly one response must exist for every FOUND manifest ID.
- Unknown, duplicate, missing, malformed, or escaping response files reject the batch before partial processing.
- `image_id` must match the manifest exactly.
- Extra fields are rejected.
- `delta_ev` must be finite and within configured bounds.
- `confidence` must be within `[0, 1]`.
- Low confidence or any risk flag downgrades automatic action to REVIEW.
- Manifest order is preserved in canonical analysis artifacts.
- Preview byte count and SHA-256 are verified before importing each response.
- Preparation records SHA-256 for `selection.json`, `manifest.json`, `AI_TASK.md`, `AI_SKILLS.md`, and `decision-schema.json`.
- Saved-job process/apply recalculates every immutable artifact hash before reading decisions. A missing or altered artifact invalidates the job and fails closed.

The AI never writes RAW, XMP, catalog, cache, selection, manifest, task, skill, schema, or preview files. Its only writable output is the job-scoped `decisions/` directory.
