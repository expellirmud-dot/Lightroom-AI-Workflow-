# AI Judge Contract — Lightroom AI Exposure MVP

## Overview

The vision AI judge receives a list of Lightroom-rendered JPEG previews and returns exactly one decision per image. The AI is an untrusted input source — all output must be schema-validated before use.

## Input Contract

The judge receives an ordered list of preview image paths (or a manifest listing). The judge **must not** invent filenames or paths — it may only reference image IDs that appear in the manifest.

### Manifest format (reference)

```json
[
  {
    "image_id": "PTO_3392",
    "raw_path": "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo\\PTO_3392.NEF",
    "xmp_path": "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo\\PTO_3392.xmp",
    "preview_path": "runtime/jobs/.../previews/000001__PTO_3392.jpg",
    "sequence": 1
  }
]
```

## Output Contract

The judge returns a JSON object with an `images` array. Each entry has exactly these fields:

```json
{
  "image_id": "PTO_3392",
  "subject_type": "person",
  "subject_exposure": "SLIGHTLY_UNDEREXPOSED",
  "background_exposure": "BALANCED",
  "scene_intent": "outdoor_daylight",
  "highlight_risk": "low",
  "group_id": "group1",
  "reference_image_id": "PTO_3392",
  "recommended_delta_ev": 0.25,
  "action": "APPLY",
  "confidence": 0.91,
  "reason": "Slight underexposure of the main subject.",
  "relevance_class": "KEEP_PRIMARY",
  "quality_action": "APPLY",
  "event_relation": "same_event",
  "test_shot_likelihood": "none",
  "accidental_likelihood": "none",
  "quality_flags": [],
  "duplicate_of": ""
}
```

### Field Specifications

| Field | Type | Required | Constraint |
|-------|------|----------|------------|
| `image_id` | `string` | Yes | Must match exactly one manifest `image_id`. No invented IDs. |
| `subject_type` | `string` | Yes | Describes the main subject (e.g., person). |
| `subject_exposure` | `string` | Yes | `ExposureClass` enum value. |
| `background_exposure` | `string` | Yes | `ExposureClass` enum value. |
| `scene_intent` | `string` | Yes | `SceneIntent` enum value. |
| `highlight_risk` | `string` | Yes | `HighlightRisk` enum value (low, medium, high). |
| `group_id` | `string` | Yes | Identifier for the visual batch grouping. |
| `reference_image_id` | `string` | Yes | The reference frame ID for the group. |
| `recommended_delta_ev` | `number` | Yes | Numeric. Clamped to `[-maximum_delta_ev, +maximum_delta_ev]`. |
| `action` | `string` | Yes | `Action` enum value (APPLY, REVIEW, SKIP). |
| `relevance_class` | `string` | Yes | `RelevanceClass` enum value. |
| `quality_action` | `string` | Yes | `QualityAction` enum value (APPLY, REVIEW, SKIP). |
| `event_relation` | `string` | Yes | Description of event relation. |
| `test_shot_likelihood` | `string` | Yes | Likelihood (none, low, medium, high). |
| `accidental_likelihood` | `string` | Yes | Likelihood (none, low, medium, high). |
| `quality_flags` | `list` | Yes | List of strings identifying technical issues. |
| `duplicate_of` | `string` | Yes | ID of the duplicate image, if any. |
| `confidence` | `number` | Yes | Must be in `[0.0, 1.0]`. |
| `reason` | `string` | Yes | Human-readable explanation for decisions or notable adjustments. |

### Mandatory Rules

1. **Exactly one decision** for every manifest image — no omissions, no duplicates.
2. `image_id` values must **match** manifest `image_id` values exactly. No invented IDs.
3. `recommended_delta_ev` is the *suggested change* to exposure. Positive = brighter, negative = darker.
4. `confidence` must be in the closed interval `[0.0, 1.0]`. Low-confidence decisions (`< 0.8`) must downgrade to `REVIEW`.
5. `action` specifies whether the change should be applied or reviewed. Reject/delete semantics belong to relevance triage, not exposure judgment.
6. The AI **never** writes files directly — the CLI validates and applies decisions.

## Validation Rules Applied by CLI

Before applying any decision, the CLI must:

1. Reject any decision missing required fields.
2. Reject invalid enum values.
3. Reject any decision whose `recommended_delta_ev` or `confidence` is non-numeric or non-finite.
4. Reject any decision whose `confidence` is not in `[0.0, 1.0]`.
5. Clamp `recommended_delta_ev` to `[-maximum_delta_ev, +maximum_delta_ev]`.
6. Downgrade `action` to `REVIEW` if `confidence < minimum_apply_confidence`.
7. Downgrade `action` to `REVIEW` if `highlight_risk` is `high` and delta is positive.
8. Check for large exposure jumps within groups and flag for review.
9. Reject duplicate or unknown `image_id` values.
10. Log all reviewed or rejected decisions in `result.json` with reasons.
