---
name: visual-quality-safety
description: Assess highlight/shadow safety, focus, blur, obstruction, and whether automatic exposure correction is technically safe under the current saved-job schema.
---

# Visual Quality Safety

Assess whether exposure correction is technically safe and useful. This skill
never deletes a photograph and never writes XMP.

## Required checks

- Important highlights or skin texture are irreversibly clipped.
- Important shadows or the primary subject are unreadable.
- Severe blur, missed focus, obstruction, or partial capture removes intended
  subject value.
- A proposed positive delta would worsen highlight clipping.
- A proposed negative delta would crush important shadows.
- Exposure correction cannot make the image meaningfully usable.
- Visible evidence conflicts or confidence is too low for automation.

## Current output mapping

- Technically safe for automatic exposure processing:
  `quality_verdict=KEEP`.
- Uncertain focus, recoverability, clipping, obstruction, or conflicting
  evidence: `quality_verdict=REVIEW`.
- Technically unusable for exposure processing: `quality_verdict=SKIP`.
- Set `highlight_risk=true` or `shadow_risk=true` whenever the corresponding
  risk is material; either flag prevents automatic apply.
- Describe visible technical evidence in `subject_rationale`,
  `scene_rationale`, and `reason`.
- Do not emit a historical `quality_action` or `action` field.

`AI_TASK.md` and `decision-schema.json` are authoritative for output fields.
