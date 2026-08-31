---
name: exposure-judgment
description: Judge exposure from the intended subject, scene intent, relative batch context, and highlight/shadow safety under the current generated decision schema.
---

# Exposure Judgment Skill

Use the actual Lightroom-rendered preview evidence. Do not judge exposure from
filename or average frame brightness alone.

`AI_TASK.md` and `decision-schema.json` are authoritative for the active pass.
This skill supplies visual guidance only.

## Current MVP reasoning

1. Identify the intended subject and whether a person is the visual priority.
2. Classify the lighting/scene intent needed to interpret exposure.
3. Judge subject exposure separately from background exposure.
4. Preserve legitimate atmosphere; do not normalize every dark background.
5. Check meaningful highlight/shadow exposure risk before proposing a change.
6. Compare materially similar images through the batch-consistency skill.
7. Recommend a bounded `delta_ev`; use zero when no correction is justified.
8. Use photographic `action: REVIEW` when exposure evidence is genuinely
   unresolved/unsafe.

## Current output mapping

- `action=PASS`: `delta_ev=0.0`.
- `action=ADJUST`: finite non-zero bounded `delta_ev`.
- `action=REVIEW`: `delta_ev=0.0`.
- For the current exposure-only small-preview task, set
  `relevance_verdict=KEEP` and `quality_verdict=KEEP`; do not perform culling,
  relevance, blur, focus or sharpness triage.
- Set `highlight_risk` / `shadow_risk` only from material exposure-safety
  evidence.
- Put subject observations in `subject_rationale`.
- Put scene/exposure comparison in `scene_rationale`.
- Use `scene_group_id` and `is_reference` exactly as the generated task/schema
  define them.
- Summarize the final exposure decision in `reason`.

Do not emit historical/unsupported fields such as `recommended_delta_ev`,
`subject_exposure`, `scene_intent`, `batch_consistency_group`, `group_id` or
`reference_image_id` unless a future generated schema explicitly permits them.
