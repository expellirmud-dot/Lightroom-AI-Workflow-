---
name: batch-consistency-review
description: Group materially similar images, choose reliable visual references, and keep exposure decisions consistent without flattening legitimate scene differences.
---

# Batch Consistency Review Skill

Apply this skill across the complete prepared folder, not as isolated
single-image judgments.

## Required reasoning

1. Group images by materially similar scene, lighting, location, subject, and
   photographic intent.
2. Do not force one exposure baseline across different lighting environments.
3. Choose a representative reference frame for each group. Do not use a poor,
   blocked, blurred, clipped, or atypical image as the reference.
4. Compare subject exposure, background intent, and proposed `delta_ev` within
   each group.
5. Preserve legitimate changes caused by composition, spotlighting, backlight,
   night atmosphere, or intentional silhouette.
6. Downgrade uncertain or inconsistent corrections to REVIEW.
7. Flag unexplained large adjacent exposure jumps for REVIEW.

## Current output mapping

- Store a stable group name in `batch_consistency_group`.
- Describe the comparison and reference-frame reasoning in `scene_rationale`
  and `reason`.
- Do not emit extra JSON fields such as `group_id`, `reference_image_id`, or
  `action`; `AI_TASK.md` and `decision-schema.json` define the only accepted
  output fields.
- The same inputs and ordering should produce the same grouping choices.
