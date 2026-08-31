# Vision Judgment Contract — Exposure Session Passes

## Status / execution authority

The current canonical MVP contract is the **captured pass**:

- `AI_TASK.md` — current task/mode instructions;
- `decision-schema.json` — exact generated JSON schema;
- `AI_SKILLS.md` — supporting visual guidance;
- `manifest.json`, contact sheets and previews — immutable evidence.

This document records durable semantics. If it ever disagrees with the generated
pass schema/task, fail closed and reconcile the source/documentation; do not
invent fields from this document.

The current MVP is exposure-only. Photographer/model-quality calibration and
broader relevance/blur/focus/culling work are post-MVP unless explicitly
activated by a later task.

## Provider-neutral input

A vision producer receives one immutable pass package containing task, bundled
skills, ordered manifest, generated decision schema, contact sheets/index and
Lightroom-rendered JPEG previews.

The producer may be a file-capable agent, local/free vision model, desktop/web
application or optional API adapter. Provider identity is evidence metadata, not
authority. The producer never receives Catalog/cache/original-photo mutation
permission.

## Required judgment

For each in-scope FOUND preview:

1. inspect contact sheets first for order/batch context and relative brightness;
2. open individual previews only when needed for the exposure decision;
3. identify the intended subject/person priority and legitimate scene intent;
4. compare materially similar exposure context/reference frames;
5. assess subject/background exposure and highlight/shadow exposure risk;
6. return PASS, bounded ADJUST or photographic REVIEW.

Do not infer from filename alone or invent visual facts.

The current small-preview task must **not** judge blur, focus, sharpness, image
damage, relevance, duplicates or whether a frame should be kept. For this MVP,
`relevance_verdict` and `quality_verdict` are compatibility fields and the
producer sets them to `KEEP`; unresolved exposure evidence uses
`action: REVIEW`.

## Exact current decision object

`SinglePassDecision` / generated `decision-schema.json` currently requires:

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
  "scene_rationale": "grounded scene/exposure comparison",
  "scene_group_id": "indoor-stage-01",
  "is_reference": false,
  "reason": "concise final rationale"
}
```

Extra fields are rejected by the strict schema. `session_id`, `pass_id`,
`pass_number`, `parent_pass_id`, `group_id`, `reference_image_ids`,
`group_conflict`, `suggested_split_key` and historical
`batch_consistency_group` are **not** current per-image decision fields unless a
future generated schema explicitly adds them.

Session/pass lineage lives in the immutable package/manifest/state rather than
being duplicated into every decision JSON.

## Action / delta semantics

- `PASS` — no meaningful exposure correction; `delta_ev = 0.0`.
- `ADJUST` — finite non-zero bounded exposure proposal.
- `REVIEW` — unresolved/unsafe exposure evidence; `delta_ev = 0.0`.

Highlight/shadow risk flags describe exposure-safety risk. When the current task
cannot safely authorize an exposure change, use REVIEW rather than inventing a
quality/culling verdict.

Deterministic Python validates confidence, risk, bounds, quantization, identity,
lineage and convergence. AI never owns mutation authority.

## Scene grouping / reference semantics

`scene_group_id` is a stable exposure-context label for materially similar
lighting/subject intent. `is_reference` marks a useful reference image for that
context.

Do not flatten legitimate differences between stage lighting, backlight, night
atmosphere, silhouette or intentionally different compositions. Group fields
are context only and never authorize mutation by themselves.

The current schema does not authorize AI to silently rewrite persistent session
state or emit a group-split protocol that is absent from `decision-schema.json`.

## Deterministic validation

Before apply, Python verifies the captured package/manifest identity and exact
FOUND decision set, strict schema, finite values, confidence/risk and current
session/pass lineage. Unknown, missing, duplicate, malformed, escaping or
identity-mismatched decision files fail closed before mutation.

Low-confidence/risk handling performed by deterministic validation must not be
confused with permission for the producer to perform off-scope culling or
quality triage.

## Safe outcomes

- PASS is non-mutating.
- ADJUST remains a proposal until deterministic authorization and Lightroom
  Catalog precondition checks succeed.
- REVIEW is photographic/exposure uncertainty and is non-mutating.
- Runtime/apply/verification failures are technical outcomes, not REVIEW.

AI model/provider quality evidence is deliberately separate from technical MVP
closure. Listing it as future work does not activate a Work Order automatically.
