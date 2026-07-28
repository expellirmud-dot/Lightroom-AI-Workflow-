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
  "delta_ev": 0.35,
  "confidence": 0.91,
  "reject": false,
  "reason": ""
}
```

### Field Specifications

| Field | Type | Required | Constraint |
|-------|------|----------|------------|
| `image_id` | `string` | Yes | Must match exactly one manifest `image_id`. No invented IDs. |
| `delta_ev` | `number` | Yes | Numeric. Clamped to `[-maximum_delta_ev, +maximum_delta_ev]`. |
| `confidence` | `number` | Yes | Must be in `[0.0, 1.0]`. |
| `reject` | `boolean` | Yes | `true` if the image should be suggested for rejection (blur, motion, tilt, irrelevant). |
| `reason` | `string` | No | Human-readable explanation for reject or notable adjustments. Empty string if not rejecting. |

### Mandatory Rules

1. **Exactly one decision** for every manifest image — no omissions, no duplicates.
2. `image_id` values must **match** manifest `image_id` values exactly. No invented IDs.
3. `delta_ev` is the *suggested change* to exposure. Positive = brighter, negative = darker.
4. `confidence` must be in the closed interval `[0.0, 1.0]`. Low-confidence decisions must not be applied automatically.
5. `reject` is a suggestion only in MVP — the actual Lightroom reject action is manual.
6. `reason` is mandatory when `reject` is `true`; empty string otherwise.
7. The AI **never** writes files directly — the CLI validates and applies decisions.

## Validation Rules Applied by CLI

Before applying any decision, the CLI must:

1. Reject any decision whose `delta_ev` is non-numeric.
2. Reject any decision whose `confidence` is not in `[0.0, 1.0]`.
3. Clamp `delta_ev` to `[-maximum_delta_ev, +maximum_delta_ev]`.
4. Reject decisions with `confidence < minimum_apply_confidence` (apply as "skip" with reason).
5. Reject duplicate or unknown `image_id` values.
6. Reject any decision missing required fields.
7. Log all rejected decisions in `result.json` with reasons.
