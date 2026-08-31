# Vision Judgment Contract - Exposure Session Passes

## Status

This remains the approved target contract. WO-038 implements its contact-sheet
package input and the current MVP exposure-only task; the broader target
session/group contract still requires representative Lightroom evidence.

## Provider-neutral input

The vision producer receives one immutable pass package containing the pass
task, bundled visual skills, ordered manifest, decision schema, session/group
context, contact sheets/index, render evidence, and Lightroom-rendered JPEGs.

The producer may be a file-capable agent, local/free vision model adapter, or
optional API adapter. Provider identity is evidence metadata, not authority.
The producer never receives XMP, catalog, cache, or apply permission.

## Required judgment

The producer must inspect prepared contact sheets first for order, batch
context, and relative brightness, then actual preview bytes when needed. The
current MVP task is exposure-only and must judge:

- intended subject and person priority;
- scene/event intent and legitimate atmosphere;
- persistent scene group and reference-frame relationship;
- subject/background exposure and meaningful outlier status;
- highlight/shadow safety for the exposure decision;
- residual exposure correction for the current rendered generation;
- whether evidence supports PASS, ADJUST, or REVIEW.

Filename-only inference, invented content, unsupported precision, and silent
group reassignment are forbidden. The MVP task must not assess blur, focus,
sharpness, image damage, relevance, duplicates, or whether a frame should be
kept from its small previews.

## Target decision object

One strict JSON object is required per in-scope FOUND preview:

```json
{
  "session_id": "session-...",
  "pass_id": "pass-...",
  "pass_number": 2,
  "parent_pass_id": "pass-...",
  "image_id": "4042206",
  "group_id": "indoor-stage-01",
  "reference_image_ids": ["4042198", "4042201"],
  "action": "PASS | ADJUST | REVIEW",
  "delta_ev": 0.0,
  "confidence": 0.92,
  "highlight_risk": false,
  "shadow_risk": false,
  "group_conflict": false,
  "suggested_split_key": null,
  "subject_rationale": "grounded subject observation",
  "scene_rationale": "grounded scene/reference observation",
  "reason_codes": ["WITHIN_GROUP_TOLERANCE"]
}
```

Pass 1 uses `parent_pass_id: null`. PASS and REVIEW require `delta_ev: 0.0`.
ADJUST requires a finite non-zero delta. Extra fields are rejected.

## Group persistence and split

Pass 1 establishes group membership and references. Later passes inherit them.
When new visual evidence contradicts the group, AI sets `group_conflict: true`
and returns REVIEW or proposes a bounded split key. Python alone validates and
records a split with parent group, affected IDs, evidence, and effective pass.
AI cannot silently rewrite `groups.json`.

## Pilot decision policy

The policy snapshot may initially use `0.10 EV` meaningful tolerance,
`0.05 EV` quantization, `+/-1.0 EV` per-pass limit, `+/-2.0 EV` cumulative
limit, and four passes. These are **PILOT DEFAULTS**, not model instructions or
production constants. The producer reports judgment; deterministic Python
enforces the actual validated policy.

## Deterministic validation

Before any apply, Python verifies:

- exact session/pass/parent lineage and exact in-scope image set;
- immutable task, skills, schema, group context, manifest, and preview hashes;
- preview byte/SHA evidence and render-generation readiness;
- action/delta consistency, finite values, confidence, risk flags, and bounds;
- references belong to the declared persistent group;
- prior/cumulative exposure history and oscillation/no-progress rules;
- unknown, missing, duplicate, malformed, escaping, or identity-mismatched
  decision files reject the affected pass before mutation.

## Safe outcomes

- PASS is terminal unless later session-wide evidence explicitly reopens the
  image through a new immutable pass.
- ADJUST is only a proposal until deterministic authorization succeeds.
- REVIEW is non-mutating and records the reason for owner inspection.
- Low confidence, risk, group conflict, stale/unproven render, oscillation,
  no-progress, or pilot-limit exhaustion cannot be auto-applied.

The AI writes only to the current pass decision output directory and must not
modify captured inputs or any prior pass.
