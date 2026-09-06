---
name: exposure-judgment
description: Judge Exposure2012 from the intended subject, absolute scene exposure, and whole-set visual coherence without prescribing a step-by-step reasoning method.
---

# Exposure Judgment Skill

Use the actual Lightroom-rendered preview evidence. `AI_TASK.md` and
`decision-schema.json` are authoritative for the active pass. This skill defines
photographic goals and constraints, not a mandatory reasoning sequence.

## Required outcome

The finished job should have photographically appropriate overall Exposure2012,
while images that share materially similar lighting and photographic intent
should remain visually coherent.

Every FOUND image must be genuinely evaluated. Evaluation coverage does **not**
mean every image must change. A correct no-change result is a successful result.

For each image:

- use `PASS` with `delta_ev=0.0` when its Exposure is already appropriate and it
  is not an unexplained exposure outlier in its scene;
- use `ADJUST` only when an Exposure change is actually justified;
- use `REVIEW` with zero delta when exposure evidence is genuinely unresolved or
  unsafe for automatic adjustment.

Never adjust an image merely to prove that it was processed.

## Absolute scene responsibility

For every `scene_group_id`, state an explicit absolute scene conclusion through
`scene_exposure_verdict` and `scene_delta_ev`.

- `TOO_DARK` means the scene as a whole needs a positive Exposure direction.
- `BALANCED` means the scene is already at an appropriate overall Exposure.
- `TOO_BRIGHT` means the scene as a whole needs a negative Exposure direction.
- `REVIEW` means the scene-level Exposure cannot be resolved confidently.

Consistency alone is not correctness. A group in which every image is similarly
too bright or too dark is not `BALANCED` merely because its members match each
other.

`scene_delta_ev` is an approximate shared scene-level signal and context only.
The actual mutating proposal remains each image's validated `delta_ev`.

## Photographic freedom

Use visual judgment rather than average frame brightness alone. Consider the
intended subject, faces/skin when relevant, scene atmosphere, lighting direction,
composition, and meaningful highlight/shadow risk. Preserve legitimate
intentional differences such as backlight, spotlight, silhouettes, night mood,
or materially different lighting contexts.

A reference image may help compare a scene, but the reference is not assumed to
be correctly exposed. The absolute scene conclusion must stand on its own.

Use decisive corrections when visually justified, but always respect the active
session's bounded Exposure authority. Do not invent a larger delta to force
single-pass convergence.

## Exposure-only boundary

This task is Exposure2012 only. Do not perform culling or judge blur, focus,
sharpness, duplicates, relevance, damaged frames, or keep/cull quality from the
small package previews. Set `relevance_verdict=KEEP` and
`quality_verdict=KEEP` for the current task.

External AI has visual decision authority only. It never receives Lightroom,
Catalog, preview-cache, original-photo, XMP, or mutation authority.
