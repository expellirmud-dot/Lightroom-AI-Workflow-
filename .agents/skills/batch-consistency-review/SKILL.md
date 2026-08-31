---
name: batch-consistency-review
description: Group materially similar exposure contexts, choose reliable visual references, and keep exposure decisions consistent without flattening legitimate scene differences.
---

# Batch Consistency Review Skill

Apply this skill across the prepared pass using contact sheets first, not as
isolated single-image judgments.

`AI_TASK.md` and `decision-schema.json` are authoritative for output fields.

## Required reasoning

1. Group images by materially similar lighting, location, subject and
   photographic intent.
2. Do not force one exposure baseline across different lighting environments.
3. Choose a useful exposure reference; avoid atypical/clipped frames when that
   would distort the exposure comparison.
4. Compare subject exposure, background intent and proposed `delta_ev` within
   each group.
5. Preserve legitimate composition, spotlight, backlight, night atmosphere and
   silhouette differences.
6. Use `action: REVIEW` with zero delta when exposure consistency is genuinely
   unresolved.
7. Flag unexplained large relative exposure jumps through the rationale rather
   than inventing fields.

## Current output mapping

- Store the stable current context label in `scene_group_id`.
- Set `is_reference=true` only for a suitable reference image under the current
  pass task/schema.
- Describe comparison/reference reasoning in `scene_rationale` and `reason`.
- `action` is a required current field; it is not historical.
- Do not emit `batch_consistency_group`, `group_id`, `reference_image_id`,
  `reference_image_ids`, `group_conflict` or `suggested_split_key` unless a
  future generated schema explicitly permits them.

Grouping/reference fields provide exposure context only; they never authorize
mutation.
