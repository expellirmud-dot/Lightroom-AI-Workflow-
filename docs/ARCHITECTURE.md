# Architecture — Provider-Agnostic Exposure Sessions

## Status boundary

The canonical Exposure Session/package runtime is implemented and technical-MVP
live verification closed through WO-039. Representative Lightroom evidence
proved real absolute Catalog `Exposure2012` confirmation, `RERENDER_REQUIRED`,
and fresh Pass 2 package generation.

WO-040 completed a post-MVP correctness remediation at the visual-evidence boundary and is `LIVE_VERIFIED`.
The Lightroom preview cache stores raw root-pixel JPEG bytes separately from an
`ImageCacheEntry.orientation` code. Canonical extraction now preserves the raw
render fingerprint for freshness while rotating only the durable package JPEG to
Lightroom's intended display orientation before contact-sheet construction.

## WO-041 iteration correctness boundary

The canonical component ownership is unchanged, but iteration settlement is now
scene-complete:

- each session freezes one source-folder identity/path set; later captures must
  exactly match it or start a new session;
- each accepted pass contains the complete frozen image set so PASS and REVIEW
  decisions remain re-auditable;
- explicit scene verdict fields are AI evidence; deterministic Python checks
  their structural consistency but does not decide photographic correctness;
- render freshness is required only for prior ADJUST images; stale hashes are a
  technical `WAITING_FOR_RERENDER` condition and never mutate photographic state;
- convergence is true only when every session image is PASS.

The Lightroom plug-in surfaces these distinctions in version `1.2.11`. WO-041
remains pending representative live Lightroom validation.

## Canonical runtime flow

```text
Lightroom — Diagnose Current Folder
→ bounded readiness evidence

Lightroom — Prepare AI Package
→ capture source-folder/image identity + Catalog Exposure2012
→ Python snapshots Previews.lrdata read-only
→ identity mapping + Lightroom-rendered JPEG extraction + orientation lookup
→ preserve raw render SHA; normalize durable preview orientation
→ normalized preview byte/SHA/decode validation
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
| Cache extractor | validated read-only SQLite snapshots, ID-to-preview/orientation mapping, raw render fingerprint, orientation-normalized durable JPEG extraction and byte/SHA evidence |
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
configured preview-cache databases read-only and reconciles one exact
`ImageCacheEntry` UUID + digest + orientation record. Canonical package
preparation then reuses an already-rendered Lightroom preview file from that
identity's cache bucket; it does not ask Lightroom or Python to render a new
photographic preview.

`preview_size` is a minimum source-tier target and is currently 1440 px. An
exact `_1440` tier wins; otherwise Python selects the smallest existing larger
tier (for example `_1920`). A smaller cached tier is never silently substituted.
If no adequate tier exists, preparation returns `PREVIEW_TIER_NOT_READY` and no
immutable pass is admitted.

The SHA-256 of the selected cached source render is stored as
`source_preview_sha256`, and `source_preview_tier` records the selected tier.
For `AB` orientation the durable package JPEG is byte-identical to that cached
render. For supported rotated orientations (`BC`, `CD`, `DA`), only the durable
package artifact is orientation-normalized; mirrored/unknown codes fail closed.
The normalized package artifact receives its own byte/SHA/decode integrity
evidence and feeds ordered contact sheets/index. Temporary SQLite snapshots are
removed after package validation while durable package evidence remains.

Legacy RootPixels extraction remains compatibility tooling only. `.lrdata` is
never a writable target.

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

Freshness uses the selected Lightroom-rendered source preview SHA (`source_preview_sha256`) rather
than the orientation-normalized package artifact SHA. Historical pre-WO-040
manifests fall back to their `preview_sha256`, which was byte-identical to the raw RootPixels JPEG under the old extractor. This preserves existing session
lineage while preventing orientation normalization itself from being mistaken
for a new Lightroom render.

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
