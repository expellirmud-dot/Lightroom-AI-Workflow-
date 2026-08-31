# Mutation Safety Contract — Canonical Catalog Route and Legacy XMP

## Status

The canonical WO-034+ iterative route is **Lightroom Catalog-authoritative**.
It does not require XMP Save Metadata / Read Metadata synchronization before an
Exposure Session can run.

This file remains a high-authority safety contract because it also preserves the
older transactional XMP rules for legacy WO-029 commands. The two mutation
models must not be mixed.

## Canonical iterative mutation boundary

For `Prepare AI Package` / `Import / Apply AI Results` / `Prepare Next AI
Package`:

- Lightroom is the authoritative renderer and Catalog-visible Develop state.
- The only writable Develop property is `Exposure2012`.
- Catalog database files are never opened or modified directly.
- RAW/JPEG originals and `.lrdata` remain immutable.
- External AI has no mutation authority.
- Python plans/validates; Lightroom SDK performs the actual Develop mutation.

PASS, REVIEW and zero-change outcomes never request a Develop mutation.

## Canonical Catalog apply gate

Before an ADJUST may mutate Lightroom, reconcile:

- exact session ID, pass ID, pass number and parent lineage;
- frozen source-folder/image identity and exact current pass manifest/decision
  set;
- immutable task/skill/schema/manifest/preview/package evidence;
- current Catalog `Exposure2012` against the expected pre-apply value;
- bounded finite policy, confidence/risk and deterministic authorization.

Any material identity, lineage, schema, package or Catalog-drift mismatch fails
closed before mutation.

The apply plan uses an **absolute target**:

```text
target_exposure2012 = validated expected absolute Catalog value
```

Inside Lightroom write access, the plug-in may request only:

```lua
photo:applyDevelopSettings({ Exposure2012 = target })
```

## Post-commit verification barrier

Real Lightroom evidence established that an immediate `getDevelopSettings()`
read inside the same `withWriteAccessDo()` callback may still show the old
value. Therefore:

1. the write callback validates the precondition and requests the target;
2. verification occurs only after the callback returns;
3. verification polling is bounded;
4. an already-present absolute target is idempotently verified on retry without
   applying another delta;
5. session confirmation advances only when every required planned item is
   `APPLIED_VERIFIED`;
6. timeout/apply/read failures remain technical outcomes and never become
   photographic REVIEW merely to converge the session.

## Canonical render freshness barrier

A confirmed adjusted pass ends at `RERENDER_REQUIRED`. A later pass may be
prepared only when:

1. current Catalog `Exposure2012` matches the session's expected value;
2. a valid new Lightroom preview generation is captured;
3. render/preview evidence is linked to the new pass and passes integrity
   checks.

Stale/unproven rendering fails closed. XMP state is not part of this canonical
render gate.

## Convergence / oscillation safety

Python enforces cumulative exposure history, bounds, quantization,
oscillation/no-progress and pass limits. AI proposes photographic decisions but
does not own mutation authority or convergence policy.

A technical execution failure is not a photographic REVIEW decision. A genuine
photographic REVIEW remains non-mutating.

## Legacy transactional XMP boundary

The historical WO-029 sidecar workflow remains available only for compatibility.
When a legacy command explicitly invokes the XMP route, its established safety
procedure still applies:

1. Require exactly one finite `crs:Exposure2012` in the sidecar.
2. Verify current value/hash against the authorized legacy job evidence.
3. Read/hash original bytes.
4. Create and verify a backup.
5. Change only `crs:Exposure2012` in a validated temporary file.
6. Atomically replace the sidecar.
7. Parse and verify the exact target/final hash.
8. Roll back from the verified backup after post-write failure.
9. Halt on rollback failure.
10. Checkpoint legacy job settlement deterministically.

Legacy sidecar mutation never authorizes changes to RAW/JPEG/DNG/TIFF/PSD
originals, EXIF or any non-Exposure2012 field.

## Legacy metadata synchronization

Catalog/sidecar synchronization safety matters only when using a legacy XMP
mutation/read-back workflow. It is **not** a prerequisite for the canonical
Catalog-authoritative iterative route.

Do not create a new metadata-sync Work Order merely because an old diagnostic,
legacy Work Order or historical XMP document reports `SYNC_UNPROVEN`. First
classify whether the active command actually uses the legacy sidecar path.
