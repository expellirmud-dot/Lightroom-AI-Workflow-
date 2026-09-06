# Canonical Exposure Session Workflow

## Current evidence boundary

The canonical package/session workflow is implemented, CI-certified and
representative-live-verified through WO-039. Technical MVP Gate A/B closed on
2026-08-31 with real Catalog apply confirmation, `RERENDER_REQUIRED`, and a
fresh Pass 2 `PACKAGE_READY` transition.

WO-040 was an Owner-selected post-MVP visual-evidence correctness gate and is now closed `LIVE_VERIFIED`. Real Pass
1 package `sess-1788482026` exposed a narrower defect: `RootPixels.jpegData`
contains unrotated JPEG pixels while `ImageCacheEntry.orientation` carries the
Lightroom display rotation. The old extractor dropped that orientation, causing
some package previews/contact-sheet tiles to appear sideways. WO-040 normalizes
only the durable package preview and preserves the raw Lightroom render
fingerprint separately for freshness checks. No Catalog/original/XMP mutation is
part of this remediation.

## Goal

Use Lightroom Classic as the authoritative renderer, save one self-contained AI
package per immutable pass, allow an external vision-capable application to
process that package later, and return only structured exposure decisions for a
guarded Catalog `Exposure2012` apply.

The Lightroom plug-in never stays alive waiting for AI.

## Active post-MVP gate — WO-041

WO-041 changes iteration semantics without changing the provider-neutral or
Catalog-authoritative architecture:

- coverage means every image is evaluated, not every image is adjusted;
- canonical session decisions include an absolute scene exposure verdict and
  scene-level correction signal;
- later passes re-audit the complete frozen session image set;
- only images actually adjusted in the prior confirmed pass require fresh render
  proof;
- unchanged adjusted previews return `WAITING_FOR_RERENDER` and no new pass is
  admitted; photographic REVIEW state is left unchanged;
- an added/removed/replaced image in the Lightroom folder scope stops the old
  session with `SESSION_SCOPE_CHANGED` and requires a new session;
- `SESSION_COMPLETE` requires every frozen-session image to be photographic PASS.

Plug-in metadata for this behavior is version `1.2.11`. The Work Order remains
ACTIVE until representative Lightroom live validation is completed.

## User workflow

```text
1. Lightroom: open the intended source-folder scope
2. Apply the desired preset / Develop baseline
3. Optional: Diagnose Current Folder
4. Lightroom: AI Exposure Assist — Prepare AI Package
5. Plug-in + Python save the immutable pass package and exit (PACKAGE_READY)
6. Run the external AI application later against that package
7. AI writes the exact decision JSON set and exits
8. Lightroom: return to the same source folder if necessary
9. Lightroom: AI Exposure Assist — Import / Apply AI Results
10. Plug-in validates decisions and builds an absolute Exposure2012 plan
11. Lightroom requests approved Exposure2012 targets
12. After the write callback, bounded verification observes committed values
13. End at SESSION_COMPLETE or RERENDER_REQUIRED
14. If rerender is required, allow Lightroom to refresh rendering
15. Lightroom: AI Exposure Assist — Prepare Next AI Package
16. Repeat until SESSION_COMPLETE or safe REVIEW/stop condition
```

There is no `WAITING_FOR_AI` listener, provider polling process or live AI
connection owned by Lightroom.

## Prepare AI Package

The Prepare command owns only the Lightroom-side capture boundary:

- resolve the intended active source-folder scope;
- enumerate eligible proprietary-RAW masters;
- capture stable Lightroom identity (`id_local`, UUID, source path);
- capture current Catalog `Exposure2012`;
- write the selection snapshot;
- invoke Python preparation with the configured `Previews.lrdata` path;
- finish only after Python returns a complete durable pass package.

Python then:

- snapshots preview-cache SQLite databases read-only;
- maps Lightroom identities to cached previews;
- extracts Lightroom-rendered JPEG bytes and resolves the same cache record's
  orientation (`AB`/`BC`/`CD`/`DA` for the supported non-mirrored rotations);
- preserves a SHA-256 fingerprint of the raw `RootPixels` JPEG for render
  freshness, then normalizes only the durable package JPEG to Lightroom display
  orientation;
- validates normalized preview byte/SHA/Pillow evidence and records raw-render plus normalized-artifact hashes in the manifest; orientation is consumed during deterministic extraction;
- builds ordered 4×4 contact sheets from those normalized durable previews and
  writes `contact-sheet-index.json`;
- writes manifest, task, bundled skills, decision schema, pass state and
  `decisions/` beneath the session/pass directory;
- validates the complete package and removes temporary cache snapshots.

At `PACKAGE_READY`, no AI provider has been called and no Develop setting has
been changed.

## Durable package layout

```text
runtime/sessions/<session-id>/
|-- session.json
|-- selection.json
`-- passes/
    |-- 0001-<pass-id>/
    |   |-- selection.json
    |   |-- pass-state.json
    |   |-- manifest.json
    |   |-- AI_TASK.md
    |   |-- AI_SKILLS.md
    |   |-- decision-schema.json
    |   |-- previews/
    |   |-- contact_sheets/
    |   |-- contact-sheet-index.json
    |   `-- decisions/
    `-- 0002-<pass-id>/
```

The pass directory is the IPC contract. Lightroom may be closed after Prepare.

## External AI phase

The AI runner is separate from the Lightroom plug-in. It must:

- read the immutable task/skills/manifest/schema;
- inspect contact sheets first for ordered batch context and relative exposure,
  then individual preview bytes when needed;
- write exactly one valid decision per in-scope preview;
- never modify manifest, preview, task, schema, session, Catalog, original photo
  or cache data.

The current MVP is exposure-only. Small package previews must not be used for
culling or blur/focus/sharpness/relevance/duplicate judgments. Provider/model
quality is a separate evidence problem and is not required to prove the core
filesystem/Lightroom workflow.

## Import / Apply AI Results

This command never prepares a new pass.

It:

1. resolves the latest prepared session/pass;
2. refuses incomplete results as `AI_RESULTS_NOT_READY` without mutation;
3. requires matching active Lightroom source-folder identity;
4. validates/freezes the exact decision set through Python;
5. builds a deterministic absolute Catalog apply plan;
6. re-reads current Catalog `Exposure2012` and fails closed on drift;
7. inside Lightroom write access, requests only `{ Exposure2012 = target }`;
8. after the write callback returns, performs bounded committed-value
   verification;
9. treats an already-present absolute target as idempotently verified rather
   than applying another delta;
10. records technical verification failure as technical evidence, never
    photographic REVIEW merely for convergence;
11. asks Python to confirm the complete verified apply set;
12. exits at `SESSION_COMPLETE` or `RERENDER_REQUIRED`.

Session confirmation is fail-closed. Partial/unverified planned apply evidence
must not advance session history/state.

### WO-039 recovery boundary

The known pre-WO-039 live session may repair only image IDs recorded in its own
failed Catalog apply evidence. Recovery rebuilds result truth from current
Lightroom Catalog state. It does not trust a stale result file and does not
blindly apply the prior delta again.

## Prepare Next AI Package

A later pass may run only when:

- the session is not converged;
- the prior pass has valid confirmed apply evidence;
- pass budget remains;
- the same Lightroom source-folder scope is active.

The command captures current Catalog `Exposure2012` and invokes the existing
next-pass preparation path. Python enforces render freshness before accepting a
new preview generation. Since WO-040, freshness compares the raw Lightroom
root-pixel fingerprint rather than the orientation-normalized package artifact
hash, preventing a rotation/re-encode from falsely proving a rerender.
Stale/unproven rendering fails closed.

Successful later-pass preparation ends at `PACKAGE_READY`. External AI again
runs separately.

## Decision meanings

- `PASS` — evaluated and no Exposure change is needed; delta is zero.
- `ADJUST` — evaluated and a bounded Exposure change is proposed; it may enter deterministic planning.
- `REVIEW` — evaluated but photographic Exposure remains unresolved/unsafe for automatic action; no mutation.

Technical runtime/apply/verification failures are not REVIEW decisions.

## Safety invariants

- Lightroom remains the authoritative renderer and Catalog-visible Develop
  state.
- Catalog database files are never opened/modified directly.
- `.lrdata` is read only through validated snapshots.
- RAW/JPEG originals are never modified.
- Canonical iterative mutation changes only Catalog `Exposure2012`.
- AI has no mutation authority.
- Import/Apply never captures the next pass automatically.
- Prepare commands never import/apply AI decisions.
- Runtime packages, previews, decisions, logs and evidence remain untracked.
- Legacy XMP Save/Read Metadata behavior is not a prerequisite for the
  canonical Catalog route.

## Current terminal gate

No preview-orientation gate remains. WO-040 closed on fresh Lightroom session `sess-1788485733` with 34/34 valid previews and visual confirmation across all three contact sheets:

```text
read-only ImageCacheEntry orientation reconciliation
→ automated AB/BC/CD/DA normalization + fail-closed unsupported cases
→ raw render fingerprint preserved separately from normalized artifact SHA
→ full regression/integration/config/compile/diff gates green
→ normal Lightroom Prepare AI Package
→ 34/34 previews present
→ three uploaded contact sheets SHA-match runtime artifacts
→ 34/34 visually confirmed in Lightroom-intended orientation
→ WO-040 COMPLETE_LIVE_VERIFIED
```

The pre-fix `sess-1788482026` package remains immutable evidence and must not be
rewritten in place or used for AI exposure decisions.
