# Canonical Exposure Session Workflow

## Current evidence boundary

The iterative session/pass runtime exists in source and automated CI evidence
through WO-034..036, but representative Lightroom Classic end-to-end evidence
is still pending. WO-037 decouples the Lightroom commands from external AI
execution without testing any AI provider/model.

## Goal

Use Lightroom Classic as the authoritative renderer, save a self-contained AI
package to disk, let an external vision-capable application process that package
later, and return only structured decisions for guarded `Exposure2012`
application.

The Lightroom plug-in must never stay alive waiting for AI.

## User workflow

```text
1. Lightroom: open exactly one source folder
2. Apply the desired Lightroom preset / Develop baseline
3. Lightroom: AI Exposure Assist — Prepare AI Package
4. Plug-in + Python save one durable pass package and exit (PACKAGE_READY)
5. Run the external AI application later and point it at that package
6. AI writes decision JSON into the pass decisions folder and exits
7. Lightroom: reopen the same source folder if necessary
8. Lightroom: AI Exposure Assist — Import / Apply AI Results
9. Plug-in validates and applies only verified Exposure2012 targets
10. If another pass is required, stop at RERENDER_REQUIRED
11. After Lightroom rerenders: AI Exposure Assist — Prepare Next AI Package
12. Repeat steps 5-11 until SESSION_COMPLETE or REVIEW
```

There is no `WAITING_FOR_AI` listener, polling process, or live provider
connection owned by Lightroom.

## Prepare AI Package

The Prepare command owns only the Lightroom-side capture boundary:

- resolve exactly one active `LrFolder`;
- enumerate eligible proprietary-RAW masters;
- capture stable Lightroom identity (`id_local`, UUID and source path);
- capture current Catalog `Exposure2012`;
- write a selection snapshot;
- invoke Python preparation with the configured `Previews.lrdata` path;
- finish after Python returns a durable pass package.

Python then:

- snapshots the preview-cache SQLite databases read-only;
- maps Lightroom identities to cache previews;
- extracts and validates Lightroom-rendered JPEG previews, including byte/SHA
  evidence and Pillow decode;
- builds ordered 4×4 contact sheets and `contact-sheet-index.json` from those
  validated previews;
- writes manifest, task, bundled skills, decision schema, pass state and decision
  directory beneath the session/pass directory;
- validates the complete package, then removes temporary `cache_snapshots/`.

At this point the package is `PACKAGE_READY`. No AI provider is called and no
Develop setting is changed.

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

The pass directory is the IPC contract. Lightroom may be closed after Prepare
because the external AI receives all pass input from disk.

## External AI phase

The AI runner is a separate application/process and is not launched by the
Lightroom plug-in. It must:

- read `AI_TASK.md`, `AI_SKILLS.md` and `manifest.json`;
- inspect contact sheets first for ordered batch context and relative exposure,
  then individual extracted previews only when needed;
- write exactly one valid decision per in-scope FOUND preview to `decisions/`;
- never change manifest, preview, task, schema, session, Catalog, RAW or cache
  data.

Provider/model/transport choice is outside the Lightroom command lifecycle.
The current MVP task is exposure-only: it must not cull/reject images or judge
blur, focus, sharpness, damage, duplicates, or relevance from small previews.

## Import / Apply AI Results

This command does not prepare previews and does not create a new pass.

It:

1. resolves the latest prepared session/pass;
2. refuses incomplete decisions as `AI_RESULTS_NOT_READY` without mutation;
3. requires the same active Lightroom source folder;
4. validates/freezes the exact external decision set through Python;
5. builds a deterministic Catalog apply plan;
6. drift-checks the current Catalog Exposure2012 for each target;
7. applies only `{ Exposure2012 = target }`;
8. reads the value back and records Lightroom-observed confirmation;
9. exits at `SESSION_COMPLETE` or `RERENDER_REQUIRED`.

A confirmed pass is never silently re-applied.

## Prepare Next AI Package

A later pass is explicit. It may run only when:

- the current session is not converged;
- the current pass has verified Catalog apply evidence;
- the maximum-pass policy is not exhausted;
- the same Lightroom source folder is active.

The command captures current Catalog Exposure2012 and calls Python's existing
`--prepare-session-pass` path. Python enforces the render freshness barrier
before accepting the new preview generation. If freshness is not proven, the
command fails closed and does not advance the pass.

Successful later-pass preparation ends at `PACKAGE_READY` and exits. External
AI is again run separately.

## Decision meanings

- `PASS` — no meaningful exposure change is justified; delta is zero.
- `ADJUST` — a bounded change is justified and may enter deterministic apply
  planning.
- `REVIEW` — automatic action is unsafe or unresolved; no mutation.

Relevance/quality/photographic-intent fields remain supporting AI judgment; AI
output is always untrusted until schema, identity and lineage validation pass.

## Safety invariants

- Lightroom remains the authoritative renderer.
- `.lrdata` is read through validated snapshots only and is never written.
- Catalog database files are never opened or modified directly.
- RAW/JPEG originals are never modified.
- The WO-037 iterative apply bridge can change only Catalog `Exposure2012`.
- AI has no mutation authority.
- Import / Apply never captures a next pass automatically.
- Prepare commands never import/apply AI decisions.
- Runtime packages, previews, decisions, logs and evidence remain untracked.

## Deferred work

WO-037 deliberately does not decide AI model quality, batching strategy,
reference-retrieval redesign, contact-sheet policy or provider transport. Those
can be improved independently because the package contract is now separated
from Lightroom execution.
