# Canonical Exposure Session Workflow

## Current evidence boundary

The explicit package/session workflow is implemented and CI-certified through
WO-039. Representative Lightroom evidence has reached a 324-image decision and
Catalog-apply stage. The 21 requested absolute Exposure2012 targets were observed
in Lightroom, but the pre-WO-039 code verified too early inside the write
callback and recorded stale values.

WO-039 fixes that verification boundary in CI. The remaining live gate is to
re-run the affected Import/Apply recovery and then prove a fresh next-pass render
generation. The workflow is therefore in MVP closure/live certification rather
than initial implementation.

## Goal

Use Lightroom Classic as the authoritative renderer, save one self-contained AI
package per immutable pass, allow an external vision-capable application to
process that package later, and return only structured exposure decisions for a
guarded Catalog `Exposure2012` apply.

The Lightroom plug-in never stays alive waiting for AI.

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
- extracts and validates Lightroom-rendered JPEG previews including byte/SHA
  evidence and Pillow decode;
- builds ordered 4×4 contact sheets and `contact-sheet-index.json`;
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
new preview generation. Stale/unproven rendering fails closed.

Successful later-pass preparation ends at `PACKAGE_READY`. External AI again
runs separately.

## Decision meanings

- `PASS` — no meaningful exposure change; delta is zero.
- `ADJUST` — a bounded exposure change is proposed and may enter deterministic
  planning.
- `REVIEW` — photographic evidence is unsafe/unresolved for automatic action;
  no mutation.

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

Before starting a new implementation Work Order for this path, close or record a
precise stop condition for the current live gate:

```text
WO-039 re-run Import / Apply
→ 21 APPLIED_VERIFIED without second delta
→ PASS 303 / REVIEW 0
→ RERENDER_REQUIRED
→ Lightroom rerender
→ Prepare Next AI Package
→ fresh generation accepted
```

A defect inside this same acceptance path is remediation of the active gate by
default, not an automatic reason to create another Work Order.
