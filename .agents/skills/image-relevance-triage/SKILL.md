---
name: image-relevance-triage
description: Judge event relevance, documentary value, accidental/test-shot evidence, duplicates, and whether exposure processing should continue under the current saved-job schema.
---

# Image Relevance Triage

Assess relevance from the actual image and its batch context. Rejection is a
suggestion only; this project never deletes or rejects photographs in
Lightroom.

## Required reasoning

1. Determine whether the image belongs to the same event, subject, location, or
   narrative context as its batch.
2. Distinguish primary, supporting, and candid documentary value.
3. Identify likely test shots, accidental captures, irrelevant frames, and
   duplicates using multiple visible indicators rather than filenames.
4. Separate an intentional candid or unusual composition from an unintended
   capture.
5. Consider whether the image remains worth exposure processing even when it
   has a technical weakness.
6. Use REVIEW for ambiguous or conflicting evidence.

## Current output mapping

- Relevant primary, supporting, or candid image: `relevance_verdict=KEEP`.
- Ambiguous test shot, possible accidental capture, uncertain duplicate, or
  uncertain event relationship: `relevance_verdict=REVIEW`.
- Confidently irrelevant, accidental, duplicate with no independent value, or
  unusable frame: `relevance_verdict=SKIP`.
- Record visible evidence in `subject_rationale` and the final classification
  rationale in `reason`.
- Do not emit historical extra fields such as `relevance_class`,
  `event_relation`, `test_shot_likelihood`, `accidental_likelihood`,
  `duplicate_of`, or `quality_flags`; incorporate that evidence into the
  accepted rationale fields.

`AI_TASK.md` and `decision-schema.json` are authoritative for output fields.
