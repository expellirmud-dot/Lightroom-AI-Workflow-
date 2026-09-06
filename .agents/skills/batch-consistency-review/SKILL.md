---
name: batch-consistency-review
description: Keep materially similar exposure contexts coherent across the whole pass while preserving legitimate scene differences and absolute scene correctness.
---

# Batch Consistency Review Skill

Use contact sheets and individual previews as useful evidence, but do not treat
any particular inspection order as mandatory. `AI_TASK.md` and
`decision-schema.json` define the active output contract.

## Required outcome

Group images that materially share lighting and photographic intent so their
Exposure can be judged in context. The grouping exists to prevent unexplained
brightness jumps and skipped images, not to force every frame toward one global
numeric value.

For each scene group:

- every member must be genuinely evaluated;
- the group must have one explicit absolute exposure conclusion;
- obvious within-scene exposure outliers must not be silently ignored;
- legitimate differences in composition, subject placement, spotlight,
  backlight, silhouette, night atmosphere, or changed lighting may justify a
  separate group or a different per-image delta;
- a useful reference image may assist comparison, but reference matching alone
  is never proof that the scene is correctly exposed.

`PASS` means checked and no adjustment needed. It is not a placeholder for an
image that was not considered. `ADJUST` is used only for images that actually
need an Exposure change. `REVIEW` is unresolved photographic exposure evidence.

## Scene fields

Use a stable `scene_group_id` for each materially similar exposure context. All
members of that group must agree on:

- `scene_exposure_verdict`: `TOO_DARK`, `BALANCED`, `TOO_BRIGHT`, or `REVIEW`;
- `scene_delta_ev`: the approximate shared scene-level correction signal.

Per-image `delta_ev` remains free to differ from the scene signal. A genuinely
well-exposed frame can remain PASS even when other members of the same broader
context need adjustment.

## Boundary

Grouping and reference fields provide visual context only; they never authorize
mutation. Do not emit unsupported group-management fields or expand the task
into culling, focus/blur, relevance, duplicate, or general image-quality review.
