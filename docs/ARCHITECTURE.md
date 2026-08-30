# Architecture - Provider-Agnostic Exposure Sessions

## Status boundary

The Exposure Session architecture is the approved target and is `PLANNED`.
Current source at `main` still implements WO-029's prepared-folder single-pass
workflow. Documentation must not use target existence as implementation proof.

## Canonical target flow

```text
Lightroom active folder
-> DIAGNOSE_CURRENT_FOLDER
-> immutable session identity
-> read-only Lightroom cache snapshot for pass N
-> Lightroom-rendered preview manifest + render evidence
-> provider-neutral external vision decision files
-> deterministic pass/convergence validation
-> guarded ADJUST-only XMP transactions
-> Lightroom metadata refresh
-> render freshness barrier
-> next immutable pass or terminal PASS/REVIEW
```

## Component ownership

| Component | Target responsibility |
|---|---|
| Lightroom plug-in | folder diagnostics, Lightroom identity, thin session coordination, explicit apply request, metadata refresh, render-generation coordination |
| Diagnostic controller | aggregate Lightroom, eligibility, cache, XMP-readiness, runtime, CLI, and bridge evidence without fail-fast suppression |
| Cache extractor | read-only SQLite snapshots, ID-to-preview mapping, JPEG extraction, byte/hash and generation evidence |
| Session controller | immutable selection, pass lineage, group ledger, policy snapshot, state transitions, safe resume |
| External vision AI | actual visual inspection, scene/event grouping, references, intent, outlier judgment, PASS/ADJUST/REVIEW output only |
| Optional adapters | translate local/free/API model execution into the same file contract; no XMP authority |
| Deterministic Python | schema/exact-set validation, render freshness, convergence, oscillation, bounds, authorization, evidence |
| XMP transaction layer | backup, SHA-256 verification, temporary write, atomic Exposure2012 replace, post-write verification, rollback |
| Lightroom | authoritative rendering and final catalog-visible image state |

## Provider boundary

The canonical boundary is a filesystem pass package, not an in-process
provider interface. A producer declares informational model/adapter metadata
but receives no additional authority. Credentials and network behavior belong
only to optional adapters and are never required by the core, plug-in, session,
or XMP layers.

## Session and pass model

One session maps to one active source folder and one frozen ordered eligible
set. Passes are append-only children. Each pass records `session_id`,
`pass_id`, `pass_number`, `parent_pass_id`, input artifact hashes, policy hash,
captured previews, render evidence, decisions, and terminal outcomes.

Pass 1 sees the complete analyzable folder. Later passes see unresolved images
plus their stable group references. Groups persist unless deterministic
evidence records a safe split or the affected images move to REVIEW.

## Render freshness barrier

An adjusted image cannot enter the next AI judgment merely because a JPEG hash
changed. The controller must reconcile:

1. the expected XMP Exposure2012 and prior apply evidence;
2. a new pass/render generation identity linked to the prior pass;
3. refreshed preview byte/hash evidence captured from that generation.

Failure is `REVIEW_RENDER_UNPROVEN` or a dependent-pass stop. Stale previews
must never create a second automatic correction.

## Metadata synchronization boundary

The transaction layer can prove that it changed only Exposure2012 bytes in the
sidecar, but Lightroom `readMetadata()` may import other sidecar fields if the
catalog and sidecar were not synchronized. Preflight must therefore prove sync
safety with available evidence or fail closed. It must require an owner Save
Metadata action only when evidence shows that action is needed.

## Preserved architecture

- exactly one active Lightroom folder and direct-photo scope;
- proprietary-RAW sidecar-only boundary;
- read-only preview-cache snapshots and identity mapping;
- ordered manifests and preview byte/SHA verification;
- provider-neutral external file handoff principle;
- exact identity/path containment and two-key apply authorization;
- sequential transactional XMP backup/write/verify/rollback/checkpoint;
- final export remains manual.

## Superseded target assumptions

- prepare once and never recapture previews;
- one decision/apply settlement for the lifetime of a job;
- `SinglePassDecision` as the canonical schema;
- global latest-prepared-job pointer as session authority;
- provider selection and API credentials in the canonical core path;
- preview hash alone as sufficient rerender evidence;
- Git dirty status alone as a repository stop condition.

Legacy source may retain these paths for compatibility until a later Work Order
implements and validates the target architecture.

## No resident AI requirement

The iterative lifecycle is stateful but asynchronous and file-based. The
plug-in must not host an AI process, resident server, or network client. Each
pass can pause safely for an external producer and resume only after exact
decision and lineage validation.
