# XMP Safety Rules - Exposure Session Target

## Status and preserved boundary

The existing transactional XMP implementation remains the safety foundation.
Session/pass lineage and rerender rules in this document are approved target
contracts and remain `PLANNED` until implemented and validated.

The only property the program may modify is `crs:Exposure2012`:

```text
new_exposure = existing_exposure + validated_delta_ev
```

PASS, REVIEW, and zero delta never write XMP. RAW/JPEG/DNG/TIFF/PSD originals,
Lightroom catalogs, live preview caches, EXIF, and every non-Exposure2012 field
remain immutable to this application.

## Session and pass gate

Before a pass reaches mutation, reconcile:

- exact session ID, pass ID, pass number, and `parent_pass_id`;
- frozen eligible selection and exact current pass manifest/decision sets;
- Lightroom local ID, UUID, canonical RAW/XMP paths, and source containment;
- immutable task, skill, schema, group, policy, manifest, render, and preview
  artifact hashes;
- current XMP Exposure2012 and SHA-256 against the prior pass's expected final
  evidence or the session baseline;
- ADJUST action, confidence, risk, per-pass/cumulative policy, oscillation, and
  explicit two-key authorization.

Any material mismatch fails closed before XMP transaction code is reached.

## Pilot policy

Initial design values of `0.10 EV` tolerance, `+/-1.0 EV` per pass,
`+/-2.0 EV` cumulative, and `maximum_passes = 4` are **PILOT DEFAULTS**.
They must be session policy data, not hard-coded production safety truth.

Absolute Exposure2012 bounds remain independently validated. Representative
Lightroom evidence is required before production calibration.

## Transaction procedure

Every authorized non-zero write preserves the established procedure:

1. Parse the existing sidecar and require one unambiguous finite
   Exposure2012 value.
2. Verify current value/hash against expected session/pass evidence.
3. Read and hash the original bytes.
4. Create a pass-attributed byte-preserving backup and prove its SHA-256.
5. Surgically change only the Exposure2012 serialization in a validated
   temporary file beside the target.
6. Atomically replace the original.
7. Parse the target, verify the exact expected value, and record final SHA-256.
8. Roll back from the verified backup after post-replace failure and prove the
   restored hash.
9. Halt the batch/session on rollback failure.
10. Atomically checkpoint after every image.

Evidence includes session/pass/image IDs, target and backup paths, old/delta/new
exposure, cumulative delta, original/backup/final hashes, status, and rollback
information.

Settled records are immutable within one pass. The same image may be adjusted
in a later pass only through new lineage, fresh render proof, and reconciliation
against the previous pass's verified final XMP evidence.

## Metadata synchronization barrier

Changing only Exposure2012 bytes does not by itself prove that importing an XMP
sidecar into Lightroom will leave all other catalog develop state unchanged.
Before session/apply, the coordinator must classify synchronization safety as:

- `SYNC_PROVEN` - evidence shows catalog/sidecar state is safe;
- `SYNC_REQUIRED` - evidence shows an owner metadata-save/readiness action is
  necessary;
- `SYNC_UNPROVEN` - available evidence cannot prove safety.

Only `SYNC_PROVEN` may proceed automatically. `SYNC_REQUIRED` explains the
specific evidence and required bounded owner action. `SYNC_UNPROVEN` fails
closed without assuming that Save Metadata is always necessary.

## Lightroom render freshness barrier

After `APPLIED_VERIFIED`, Lightroom refreshes metadata and becomes responsible
for the next rendered preview. An adjusted image may re-enter AI analysis only
when all of these match:

1. XMP/read-back evidence equals expected Exposure2012;
2. the next preview capture has a new pass/render generation identity linked
   to the applied pass;
3. refreshed preview evidence, including bytes and SHA-256, is valid for that
   generation.

Preview hash alone is insufficient. Missing, stale, unchanged, ambiguous, or
unlinked evidence produces REVIEW or a dependent-pass stop. The system must
never compound a correction using an unproven render.

## Convergence and oscillation safety

Python, not AI or the plug-in, enforces cumulative history. A meaningful sign
reversal, revisit of a prior exposure state, repeated no-progress residual, or
pilot-limit exhaustion removes automatic write authority and settles the image
as REVIEW. Independent safe groups may continue unless a session-wide identity,
authorization, checkpoint, or rollback invariant failed.
