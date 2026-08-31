---
name: visual-quality-safety
description: Protect exposure automation from material highlight/shadow risk; broader blur/focus/quality triage is dormant for the current small-preview MVP unless AI_TASK.md explicitly activates it.
---

# Visual Quality Safety

`AI_TASK.md` and `decision-schema.json` are authoritative for the active pass.
This skill must not expand the current task beyond exposure.

## Current MVP checks

Assess only exposure-safety evidence that is meaningful from the available
Lightroom-rendered preview:

- a positive exposure change would materially worsen important highlight
  clipping;
- a negative exposure change would materially crush important subject/shadow
  detail;
- the exposure evidence is too ambiguous for a safe automatic correction.

For the current exposure-only small-preview task:

- set `quality_verdict=KEEP`;
- do not judge blur, missed focus, obstruction, sharpness, image damage or
  whether the photograph is usable/should be kept;
- set `highlight_risk=true` or `shadow_risk=true` only when the corresponding
  exposure risk is material;
- use `action=REVIEW` with zero delta for unresolved exposure safety;
- describe the exposure-safety evidence in the permitted rationale/reason
  fields.

## Future activation boundary

Broader technical-quality triage may be used only when a future `AI_TASK.md`
explicitly activates it with suitable evidence/schema. Historical quality
examples/references do not override the current task.
