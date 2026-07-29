---
name: exposure-judgment
description: Judge a photo's exposure from intended subject, scene intent, highlight/shadow safety, and the current saved-job decision schema.
---

# Exposure Judgment Skill

Use this skill on the actual Lightroom-rendered preview. Do not judge exposure
from the filename or average frame brightness alone.

## Required reasoning

1. Identify the intended subject and whether a person is the visual priority.
2. Classify the scene intent: indoor event, outdoor daylight, stage/spotlight,
   backlit person, night/low light, documentary candid, detail/object, or
   unknown.
3. Judge subject exposure separately from background exposure.
4. Preserve legitimate atmosphere; do not normalize every dark background.
5. Check important highlights, skin, clothing, and shadow detail before
   recommending a correction.
6. Compare materially similar images through the batch-consistency skill.
7. Recommend a bounded `delta_ev`; use `0.0` when no correction is justified.
8. Return only fields permitted by `decision-schema.json`.

## Current output mapping

- Safe, useful image with a justified automatic correction:
  `relevance_verdict=KEEP`, `quality_verdict=KEEP`.
- Uncertain intent, large correction, conflicting evidence, or safety concern:
  use `REVIEW` in the affected verdict.
- Technically unusable or irrelevant image that should not receive exposure
  changes: use `SKIP`.
- `highlight_risk` and `shadow_risk` are booleans.
- Put subject observations in `subject_rationale`.
- Put scene intent, background exposure, and lighting observations in
  `scene_rationale`.
- Put the final bounded exposure decision in `delta_ev` and summarize the
  decision in `reason`.

`AI_TASK.md` and `decision-schema.json` are authoritative for field names. Do
not emit historical fields such as `recommended_delta_ev`, `action`,
`subject_exposure`, or `scene_intent` as extra JSON fields.
