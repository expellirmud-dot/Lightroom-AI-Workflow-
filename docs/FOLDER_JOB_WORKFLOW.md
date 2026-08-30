# Canonical Exposure Session Workflow

This document defines the approved target workflow. The current source and
Lightroom plug-in still implement the WO-029 prepared-folder single-pass flow;
the session/pass lifecycle below is `PLANNED`, not implemented or live verified.

## Goal

Use Lightroom Classic as the authoritative renderer, analyze exposure in
scene/event context, apply only guarded `crs:Exposure2012` changes, render again
through Lightroom, and recheck until no meaningful automatic correction
remains or difficult images are settled as REVIEW.

The workflow is provider-agnostic. A file-capable agent, a free/local vision
model adapter, or an optional API adapter may produce the same untrusted pass
decision files. No paid API or named provider is required by the core system.

## Target lifecycle

```text
DIAGNOSE_CURRENT_FOLDER
-> START_EXPOSURE_SESSION
-> CAPTURE_PASS_1_FROM_LIGHTROOM_CACHE
-> VISION_GROUP_AND_JUDGE
-> VALIDATE_PASS_DECISIONS
-> APPLY_ADJUST_ONLY
-> LIGHTROOM_METADATA_REFRESH
-> PROVE_NEW_RENDER_GENERATION
-> CAPTURE_NEXT_IMMUTABLE_PASS
-> RECHECK_UNRESOLVED_IMAGES_WITH_GROUP_REFERENCES
-> CONVERGED | REVIEW_REQUIRED | SAFE_STOP
```

No Ctrl+A selection is required. One session contains directly contained
eligible proprietary-RAW masters from exactly one active `LrFolder`.

## Phase 0 - Diagnostic-first preflight

`DIAGNOSE_CURRENT_FOLDER` is the first implementation seam. It must gather all
independent evidence that can be obtained safely in one Lightroom run and must
write machine-readable and human-readable reports even when eligible RAW count
is zero. Its detailed contract is in `docs/DIAGNOSTIC_PREFLIGHT.md`.

Diagnostics never create an exposure session, invoke AI, modify XMP, refresh
metadata, or write to the Lightroom catalog or live preview cache.

## Exposure Session

A session freezes session/source-folder identity, ordered eligible Lightroom
IDs/UUIDs/RAW/XMP paths, eligibility evidence, initial XMP value/hash evidence,
the scene-group ledger, pass lineage, and the pilot policy snapshot.

Target layout:

```text
runtime/sessions/<session-id>/
|-- session.json
|-- selection.json
|-- groups.json
|-- policy.json
|-- passes/
|   |-- 0001-<pass-id>/
|   |   |-- pass-state.json
|   |   |-- manifest.json
|   |   |-- render-evidence.json
|   |   |-- AI_TASK.md
|   |   |-- AI_SKILLS.md
|   |   |-- decision-schema.json
|   |   |-- previews/
|   |   |-- decisions/
|   |   |-- results/
|   |   `-- apply-evidence.json
|   `-- 0002-<pass-id>/
`-- xmp_backups/
```

Each pass has a unique `pass_id`, monotonic `pass_number`, and
`parent_pass_id`. Pass 1 uses `parent_pass_id: null`; every later pass points to
the immediately preceding pass. Captured pass inputs are immutable.

## Pass 1 and scene groups

Pass 1 captures every available current Lightroom-rendered preview. External
vision AI inspects the whole folder, identifies intended subjects, creates
scene/event groups, chooses reliable reference frames, and returns one
PASS/ADJUST/REVIEW decision per in-scope FOUND preview.

Scene groups persist across passes by default. If later evidence conflicts
with a group, the image becomes REVIEW or the controller records a deterministic
group split with parent group, reason, evidence, affected IDs, and effective
pass. Silent regrouping is forbidden.

## Decision meanings

- `PASS` - exposure is meaningfully consistent with scene intent and group
  references. Delta is exactly `0.0`; XMP is not written.
- `ADJUST` - a finite bounded delta is justified and all automatic safety gates
  pass. Only this state may reach XMP authorization.
- `REVIEW` - automatic action is unsafe or unresolved. Delta is exactly `0.0`;
  XMP is not written.

Unavailable/stale previews, low confidence, contradictory scene evidence,
highlight/shadow risk, oscillation, identity mismatch, and unverifiable
metadata/render state settle as REVIEW or a stricter session stop.

## Pilot convergence policy

These are **PILOT DEFAULTS**, not production constants:

- meaningful correction tolerance: `0.10 EV`;
- quantization: `0.05 EV`;
- maximum automatic delta per pass: `+/-1.0 EV`;
- maximum cumulative automatic delta per image: `+/-2.0 EV`;
- `maximum_passes = 4`;
- passes 1-3 may authorize ADJUST; pass 4 is verification-only.

Representative Lightroom evidence must calibrate production policy. Python
loads the policy snapshot, validates it, and records the exact values used.

## Apply and metadata synchronization

Before apply, Python reconciles session/pass identity, exact image sets, source
containment, prior XMP value/hash, decision state, confidence, risk, pass and
cumulative bounds, and explicit authorization. It then reuses the existing
transactional XMP procedure.

Metadata synchronization fails closed only when safe catalog/sidecar state
cannot be proven. The system must not require the owner to Save Metadata on
every run without evidence that synchronization is necessary.

## Lightroom render barrier

After `APPLIED_VERIFIED`, the plug-in refreshes Lightroom metadata for those
images. A later pass may judge an adjusted image only when all three render
freshness dimensions reconcile:

1. XMP/read-back evidence equals the expected `Exposure2012`;
2. the capture belongs to a new pass/render generation linked to the applied
   pass;
3. refreshed preview evidence, including byte/hash evidence, is present and
   consistent with that generation.

A changed preview hash alone is insufficient. If freshness cannot be proven
within a bounded wait, settle the image as `REVIEW_RENDER_UNPROVEN` or stop the
dependent pass; never apply another correction from a stale preview.

## Later passes and safe stop

Later passes capture unresolved images plus stable group references. AI judges
the residual correction against the persisted group. Python detects sign
reversal, exposure-state revisit, cumulative bounds, no-progress, and maximum
passes. Oscillating or non-improving images become REVIEW without blocking safe
independent groups unless a session-wide invariant failed.

The session stops successfully when no ADJUST remains and every image is PASS
or REVIEW. It stops safely on maximum passes, render-generation failure,
metadata-sync uncertainty, active-folder/identity mismatch, immutable artifact
change, XMP divergence, authorization failure, corrupted checkpoint, or fatal
rollback failure.

Runtime artifacts, previews, decisions, evidence, logs, and backups remain
untracked and must never be committed.
