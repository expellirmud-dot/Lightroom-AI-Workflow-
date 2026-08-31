# Architecture - Provider-Agnostic Exposure Sessions

## Status boundary

The iterative Exposure Session runtime exists in automated-tested form through
WO-034..036. Representative Lightroom Classic end-to-end evidence is still
pending, so it is not `LIVE_VERIFIED`.

WO-037 changes orchestration, not photographic judgment: the Lightroom plug-in,
Python package/session engine, and external AI are explicitly separated by a
durable filesystem pass package.

## Canonical runtime flow

```text
Lightroom — Prepare AI Package
-> capture active-folder identity + Catalog Exposure2012
-> Python snapshots Previews.lrdata read-only
-> Python maps identities and extracts Lightroom-rendered JPEG previews
-> Python validates previews and creates ordered 4×4 contact sheets
-> durable immutable pass package
-> temporary cache snapshots removed after package validation
-> PACKAGE_READY
-> Lightroom plug-in exits

External AI Runner — later / separate process
-> read pass package, task, skills, manifest, previews
-> write pass-scoped decision JSON only
-> exit

Lightroom — Import / Apply AI Results
-> verify exact session/pass/source-folder identity
-> validate and freeze external decisions
-> deterministic convergence/safety planning
-> guarded Exposure2012-only Catalog apply
-> Lightroom-observed confirmation
-> SESSION_COMPLETE or RERENDER_REQUIRED
-> plug-in exits

Lightroom — Prepare Next AI Package
-> require prior verified apply evidence
-> capture current Catalog Exposure2012
-> prove render freshness through next-pass preparation
-> read-only cache snapshot/extraction
-> next immutable pass package
-> PACKAGE_READY
-> plug-in exits
```

No command owns a resident `WAITING_FOR_AI` loop. Package readiness is a durable
filesystem condition, not an active Lightroom process state.

## Component ownership

| Component | Responsibility |
|---|---|
| Lightroom plug-in | active-folder diagnostics, Lightroom identity and Catalog Exposure2012 capture, explicit Prepare, explicit Import/Apply, explicit Prepare Next Package |
| Cache extractor | read-only SQLite snapshots, ID-to-preview mapping, JPEG extraction, byte/hash evidence |
| Session/package engine | validates JPEG previews, creates ordered contact sheets/index, removes temporary snapshots after package validation, owns immutable task/skills/schema/manifest artifacts, exact-set decision validation, safe resume data |
| External vision AI | actual visual inspection and decision JSON only; no Lightroom or mutation authority |
| Optional AI adapters | transport a pass package to/from a chosen app/model; isolated from Lightroom and mutation code |
| Deterministic Python | schema/identity validation, convergence, bounds, render barrier, evidence and planning |
| Lightroom Catalog apply bridge | drift-check current Exposure2012, apply only absolute Exposure2012 targets, verify observed values |
| Lightroom | authoritative renderer and final catalog-visible Develop state |
| Session/pass directory | durable IPC boundary between Lightroom, Python, and external AI |

## Provider boundary

The canonical boundary is a filesystem pass package, not an in-process provider
interface. The plug-in never signs in to an AI service, holds API credentials,
opens a browser, polls, or keeps a network/client process alive.

An external AI runner may execute while Lightroom is closed because all AI input
needed for that pass is already persisted. It may write only pass-scoped
`decisions/` output. It cannot modify captured inputs or Lightroom state.

## Preview-cache boundary

The plug-in does not query SQLite or decode `.lrdata` itself. It supplies stable
Lightroom identity (`id_local`, UUID, source path and Catalog Exposure2012) to
Python. Python snapshots the configured `Previews.lrdata` databases read-only,
reconciles identity, extracts the Lightroom-rendered JPEG, validates it, records
byte/SHA evidence, then creates 4×4 ordered contact sheets and their index from
those validated bytes. Once package validation succeeds it deletes the temporary
snapshot DBs; the preview evidence and sheet/index evidence remain in the pass.

`.lrdata` is never a writable target.

## Session and pass model

One session maps to one Lightroom source folder and frozen identity set. Passes
are append-only children. Each pass owns its selection, manifest, extracted
previews, task, skill bundle, schema, decisions and apply/render evidence.

Pass 1 is created only by `Prepare AI Package`. A later pass is created only by
`Prepare Next AI Package`; Import / Apply never creates a pass implicitly.

## Apply boundary

WO-037 does not redesign exposure mutation. The iterative runtime reuses the
existing Catalog-authoritative safeguards from WO-034:

- reconcile the same active source folder and image IDs;
- compare observed Catalog Exposure2012 with the expected pre-apply value;
- apply only `{ Exposure2012 = target }`;
- read the Catalog value back and require `APPLIED_VERIFIED` before session
  state advances.

No other Develop property is writable through the WO-037 commands.

## Render freshness barrier

A confirmed adjusted pass ends at `RERENDER_REQUIRED`. The user later invokes
`Prepare Next AI Package`. That command captures current Lightroom identity and
Exposure2012 and calls the existing next-pass preparation path, where Python
must prove the render barrier before admitting refreshed previews.

Failure to prove freshness fails the next-package command closed; it does not
fall back to stale previews and does not invoke AI.

## Repair isolation

The durable package boundary intentionally limits failure blast radius:

- Lightroom plug-in failure -> repair plug-in/bridge only; existing package and
  AI output remain on disk.
- cache extraction failure -> repair Python cache extractor only.
- AI app/model/transport failure -> rerun or repair the external AI runner;
  Lightroom remains untouched.
- skill/prompt failure -> regenerate decisions for the same immutable package
  under an explicit new result/provenance policy; no Lightroom capture is
  required merely to edit instructions.
- apply failure -> repair validation/apply bridge without recapturing the AI
  package unless render/input evidence itself is invalid.

## Legacy compatibility

`IterativeSession.lua` and `ResumeIterativeSession.lua` are retained as legacy
implementation surfaces during WO-037 migration but are no longer registered as
the canonical user-facing iterative commands. WO-029 single-pass commands are
also retained and explicitly labeled Legacy in the plug-in menu.
