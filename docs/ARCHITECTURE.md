# Architecture — Provider-Agnostic Exposure Sessions

## Status boundary

The canonical Exposure Session/package runtime is implemented and has automated
cross-component evidence through WO-039. A representative Lightroom live session
has already reached a 324-image decision/apply stage and showed that the 21
requested absolute `Exposure2012` targets were present in Lightroom.

The remaining current boundary is narrower: WO-039's corrected post-commit
verification must be rechecked in Lightroom, followed by a real fresh-render
`Prepare Next AI Package` proof. Do not treat the canonical session runtime as
merely `PLANNED`, but do not claim the complete iterative loop `LIVE_VERIFIED`
until those gates close.

## Canonical runtime flow

```text
Lightroom — Diagnose Current Folder
→ bounded readiness evidence

Lightroom — Prepare AI Package
→ capture source-folder/image identity + Catalog Exposure2012
→ Python snapshots Previews.lrdata read-only
→ identity mapping + Lightroom-rendered JPEG extraction
→ preview byte/SHA/decode validation
→ ordered 4×4 contact sheets + index
→ immutable pass package
→ temporary cache snapshots removed after package validation
→ PACKAGE_READY
→ plug-in exits

External AI Runner — later / separate process
→ read package/task/skills/manifest/contact sheets/previews
→ write pass-scoped decision JSON only
→ exit

Lightroom — Import / Apply AI Results
→ exact session/pass/source-folder reconciliation
→ validate/freeze decision set
→ deterministic bounds/convergence planning
→ build absolute Catalog Exposure2012 apply plan
→ inside write access: validate precondition + request target only
→ after write callback: bounded committed-value verification
→ Python confirms only APPLIED_VERIFIED evidence
→ SESSION_COMPLETE or RERENDER_REQUIRED
→ plug-in exits

Lightroom — Prepare Next AI Package
→ require prior confirmed pass + same source folder
→ capture current Catalog Exposure2012
→ prove refreshed render generation
→ read-only cache extraction
→ next immutable pass
→ PACKAGE_READY
→ plug-in exits
```

No canonical command owns a resident AI wait loop, browser session, provider
connection or unbounded Catalog verification loop.

## Component ownership

| Component | Responsibility |
|---|---|
| Lightroom plug-in | active-folder diagnostics; Lightroom identity/Catalog Exposure2012 capture; explicit Prepare, Import/Apply and Prepare Next commands; Catalog mutation request and post-commit observation |
| Cache extractor | validated read-only SQLite snapshots, ID-to-preview mapping, JPEG extraction and byte/SHA evidence |
| Session/package engine | immutable session/pass lineage, selection/manifest, task/skills/schema, contact sheets/index, package integrity and durable evidence |
| External vision AI | visual exposure judgment and decision JSON only; no Lightroom/cache/mutation authority |
| Optional AI adapters | transport outside the core; provider-specific and isolated |
| Deterministic Python | decision/schema/identity validation, convergence, bounds, oscillation/no-progress, render barrier, evidence and apply planning/confirmation |
| Catalog apply barrier | absolute-target drift check, Lightroom write request, bounded post-commit verification and idempotent retry |
| Lightroom | authoritative renderer and final Catalog-visible Develop state |
| Session/pass directory | durable IPC boundary between Lightroom, Python and external AI |

## Provider boundary

The canonical AI boundary is the filesystem pass package, not an in-process
provider interface. The Lightroom plug-in does not sign in to AI services, hold
API credentials, open a browser, poll for results or keep a provider process
alive.

An external runner may execute while Lightroom is closed because pass inputs are
persisted. It may write only the current pass `decisions/` output and cannot
modify captured inputs or Lightroom state.

## Preview/cache boundary

The plug-in never queries SQLite or decodes `.lrdata`. It supplies stable
Lightroom identity and current Catalog `Exposure2012`. Python snapshots the
configured preview-cache databases read-only, reconciles identity, extracts the
Lightroom-rendered JPEG, validates byte/SHA/decode evidence, and builds ordered
contact sheets/index. Once package validation succeeds, temporary snapshot DBs
are removed while durable preview/package evidence remains.

`.lrdata` is never a writable target.

## Session/pass model

One session maps to one Lightroom source-folder scope and frozen identity set.
Passes are append-only children. Each pass owns its selection, manifest,
previews, contact sheets/index, task, skill bundle, schema, decisions and
apply/render evidence.

Pass 1 is created only by `Prepare AI Package`. A later pass is created only by
`Prepare Next AI Package`. Import/Apply never creates a pass implicitly, and a
confirmed pass is never silently re-applied.

## Catalog apply / commit barrier

The canonical iterative route is Catalog-authoritative and separate from the
legacy XMP sidecar path.

For each planned ADJUST:

1. Python supplies `expected_before_exposure2012` and absolute
   `target_exposure2012`.
2. Lightroom re-reads the current Develop state and fails closed on drift.
3. Inside `withWriteAccessDo()`, Lightroom requests only
   `{ Exposure2012 = target }`.
4. The code does **not** declare failure or success from an immediate
   same-callback post-write read.
5. After the write callback returns, a bounded verification barrier polls the
   Lightroom-observed Develop state.
6. If the absolute target is already present during retry/recovery, it becomes
   `APPLIED_VERIFIED` without another delta.
7. Python advances session history/state only when every required planned item
   is verified.

A verification timeout or other technical failure remains a technical outcome;
it does not become photographic REVIEW merely to settle the session.

## Render freshness barrier

A confirmed non-converged pass ends at `RERENDER_REQUIRED`. The user later runs
`Prepare Next AI Package`. That command captures current Catalog state and calls
the next-pass preparation path, where Python must prove a fresh render
generation before admitting previews.

Failure to prove freshness fails closed; it does not reuse stale previews or
invoke AI.

## Repair isolation

- Lightroom command/bridge failure → repair Lightroom boundary without
  recapturing valid AI inputs unless identity/render evidence is invalid.
- cache extraction failure → repair Python cache path only.
- external AI/transport failure → rerun/repair external producer; Lightroom is
  untouched.
- task/skill quality issue → regenerate decisions under an explicit provenance
  policy; do not mutate Lightroom merely to edit instructions.
- apply verification failure → repair confirmation/recovery without blindly
  reapplying deltas or turning technical state into REVIEW.

A defect found while proving the current gate defaults to remediation within the
active Work Order when it remains inside the same boundary. Architecture repair
does not require a new Work Order merely because it was discovered during live
validation.

## Legacy compatibility

WO-029 sidecar/XMP commands and historical iterative/resume implementation files
may remain for compatibility, but they are not the canonical architecture.
Their requirements must not be copied into the current Catalog route unless an
explicit accepted decision reintroduces them.
