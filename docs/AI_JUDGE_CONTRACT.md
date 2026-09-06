# Vision Judgment Contract — Exposure Session Passes

## Status / execution authority

The canonical external-AI contract is the immutable captured pass:

- `AI_TASK.md` — active task and outcome requirements;
- `decision-schema.json` — exact generated JSON schema for the pass;
- `AI_SKILLS.md` — supporting visual guidance;
- `manifest.json`, contact sheets and previews — immutable Lightroom-rendered evidence.

If this document disagrees with the generated pass task/schema, fail closed and
reconcile the repository. Do not invent missing fields.

The current product scope is Exposure2012 only. External AI owns visual judgment
and decision JSON only. Python owns deterministic validation/safety. Lightroom
remains the authoritative renderer and Catalog-visible Develop state.

## Judgment goal

The finished job should have photographically appropriate overall Exposure, and
images that materially share scene lighting/intent should remain visually
coherent.

This is an outcome contract, not a mandatory chain-of-thought or inspection
recipe. The producer may use contact sheets, individual previews, measurements,
or any efficient visual reasoning method available to it, provided the required
outcomes below are satisfied.

## Required outcomes

For every FOUND image:

- it must be genuinely evaluated;
- a correct no-change judgment is valid and desirable;
- an Exposure change is proposed only when justified;
- unresolved/unsafe photographic exposure evidence is returned as REVIEW;
- no image may be silently omitted merely because another image is the scene reference.

For every `scene_group_id`:

- the producer must state one explicit **absolute** scene exposure conclusion;
- members must not contain unexplained exposure outliers;
- scene consistency alone is insufficient: an entire scene that is consistently
too bright or too dark is still incorrect;
- legitimate photographic differences may justify different per-image deltas or
separate scene groups.

A reference image is comparison context only. The producer must not assume the
reference itself is correctly exposed.

## Canonical session decision object

The current session pass requires one JSON decision per FOUND image:

```json
{
  "image_id": "4042206",
  "action": "PASS | ADJUST | REVIEW",
  "relevance_verdict": "KEEP",
  "quality_verdict": "KEEP",
  "delta_ev": 0.0,
  "confidence": 0.92,
  "highlight_risk": false,
  "shadow_risk": false,
  "subject_rationale": "grounded subject observation",
  "scene_rationale": "grounded scene/exposure observation",
  "scene_group_id": "indoor-stage-01",
  "scene_exposure_verdict": "TOO_DARK | BALANCED | TOO_BRIGHT | REVIEW",
  "scene_delta_ev": 0.0,
  "is_reference": false,
  "reason": "concise final rationale"
}
```

The canonical session schema marks the scene fields explicitly required. Extra
fields are rejected. Session/pass lineage remains in immutable package/session
state rather than being duplicated into each decision.

## Action semantics

- `PASS` — the image was evaluated and needs no Exposure change;
  `delta_ev = 0.0`.
- `ADJUST` — the image was evaluated and needs a finite non-zero bounded
  Exposure change.
- `REVIEW` — the image was evaluated but photographic Exposure remains
  unresolved/unsafe for automatic change; `delta_ev = 0.0`.

Coverage is **evaluation coverage**, not mutation coverage. Never adjust an
image merely to demonstrate that it was processed.

Low-confidence or material exposure-safety risk may deterministically downgrade
an adjustment to non-mutating REVIEW. Any such downgrade clears the mutation
delta.

## Absolute scene fields

`scene_exposure_verdict` expresses the absolute conclusion for the complete
scene context:

- `TOO_DARK` → positive `scene_delta_ev`;
- `BALANCED` → `scene_delta_ev = 0.0`;
- `TOO_BRIGHT` → negative `scene_delta_ev`;
- `REVIEW` → `scene_delta_ev = 0.0`.

`scene_delta_ev` is an approximate shared scene-level signal and is **not**
mutation authority. Each image's validated `action=ADJUST` and `delta_ev` remain
the only AI proposal that can enter deterministic Catalog planning.

Python validates that decisions assigned to the same `scene_group_id` do not
contradict one another on these scene-level fields. Python does not decide
whether the photographic scene verdict itself is artistically correct.

## Scene grouping / reference semantics

`scene_group_id` represents materially similar lighting and photographic intent.
`is_reference` marks a useful comparison frame only.

Do not flatten legitimate differences such as changed lighting, spotlight,
backlight, silhouette, night atmosphere, or materially different composition.
Do not use reference matching as a substitute for absolute scene judgment.

## Exposure-only boundary

The current small-preview task must not judge blur, focus, sharpness, image
damage, duplicates, relevance, or keep/cull quality. For the Exposure task,
`relevance_verdict` and `quality_verdict` remain compatibility fields set to
`KEEP`.

## Deterministic validation

Before any apply, Python verifies package integrity, exact FOUND decision set,
strict schema, image identity, finite values, scene-field structural
consistency, confidence/risk policy, bounds, session/pass lineage and Catalog
preconditions.

Missing, unknown, duplicate, malformed, contradictory, escaping or
identity-mismatched decisions fail closed before mutation.

## Iterative meaning

A later accepted pass re-audits the complete frozen session image set, including
prior PASS and REVIEW images. Prior PASS is therefore not a permanent lock; it
can be reconsidered when the scene conclusion changes.

Only images actually adjusted in the prior confirmed pass require proof of a
fresh Lightroom rerender before the next pass is admitted. Stale preview
evidence is a technical WAIT state, not photographic REVIEW.

`SESSION_COMPLETE` means every image in the frozen session is photographic PASS.
Unresolved REVIEW or a technical wait/block condition is not completion.

## Safe outcomes

- PASS is non-mutating.
- ADJUST remains untrusted input until deterministic authorization and Lightroom
  Catalog checks succeed.
- REVIEW is photographic uncertainty and non-mutating.
- Runtime, render, apply or verification failures are technical outcomes, not
  photographic REVIEW.

AI model/provider quality remains a post-MVP calibration problem separate from
core safety and workflow correctness.
