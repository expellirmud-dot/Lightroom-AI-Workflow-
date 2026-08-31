# AGENTS.md

## Project Mission

Build a Windows-first Lightroom Classic exposure assistant whose canonical MVP
workflow is:

```text
diagnose one Lightroom source-folder scope
→ Prepare AI Package
→ capture an immutable Lightroom-rendered preview pass
→ external vision AI returns provider-neutral exposure decisions
→ deterministic Python validates identity, lineage, bounds and convergence
→ Import / Apply AI Results
→ Lightroom applies only guarded absolute Exposure2012 targets
→ verify the committed Catalog value outside the write callback
→ stop at SESSION_COMPLETE or RERENDER_REQUIRED
→ Prepare Next AI Package after Lightroom rerenders
→ repeat until convergence, safe REVIEW or another explicit stop condition
```

Lightroom is the authoritative renderer and Catalog-visible Develop state. The
core must remain independent of any single AI vendor/API. The current MVP is
exposure-only.

Project Truth is not Task Truth. A Work Order is bounded execution authority;
it does not redefine the product mission or automatically create the next task.

## Authority Order and Required Read Set

Authority order:

1. Active Work Order
2. `AGENTS.md`
3. safety contracts
4. `docs/FOLDER_JOB_WORKFLOW.md` and `docs/ARCHITECTURE.md`
5. `docs/AI_JUDGE_CONTRACT.md` and `docs/DECISIONS.md`
6. `docs/ROADMAP.md`, capability/status/evidence registers
7. existing tests and implementation
8. `README.md`

Before repository-changing work:

1. Invoke or validly reuse `.agents/skills/project-read-first/SKILL.md`.
2. Read `docs/INDEX.md`.
3. Read `Work-Order/CURRENT_WORK_ORDER.md` and the active Work Order.
4. Read canonical documents whose update trigger matches the task.
5. Verify repository root, HEAD and relevant Git state.

For planning or creation of a new Work Order, also read `docs/ROADMAP.md`,
`docs/PROJECT_STATUS.md`, and the affected capability/evidence rows.

No active Work Order or unresolved conflicting authority is a stop condition for
implementation. Dirty Git state is classified by material risk rather than
blocked merely because paths are modified.

## Canonical Runtime Ownership

- Lightroom plug-in owns active-folder diagnostics, Lightroom identity and
  Catalog `Exposure2012` capture, explicit Prepare, Import/Apply and Prepare
  Next commands, and Catalog mutation/observation.
- Cache extractor owns validated read-only SQLite snapshots and Lightroom JPEG
  preview extraction. `.lrdata` is never writable.
- Session/package engine owns immutable selection/pass lineage, manifest, task,
  skill bundle, schema, package integrity, decision intake and durable evidence.
- External AI owns visual judgment and pass-scoped decision JSON only.
- Deterministic Python owns schema/identity validation, authorization,
  convergence, bounds, oscillation/no-progress policy, render freshness and
  deterministic planning.
- The session/pass directory is the durable IPC boundary.
- A pass is immutable after capture. Import/Apply never creates the next pass.

The legacy WO-029 sidecar/XMP workflow may remain for compatibility, but it is
not the canonical iterative mutation model and must not be used to infer current
session requirements.

## Catalog Apply Rules

For the canonical iterative route:

- current Catalog `Exposure2012` is the authoritative pre-apply value;
- apply plans contain absolute targets, not blind repeated deltas;
- drift from the expected pre-apply value fails closed;
- Lightroom may mutate only `{ Exposure2012 = target }`;
- the `withWriteAccessDo()` callback requests the mutation but does not declare
  success from an immediate same-callback read;
- committed-value verification occurs after the callback returns and is bounded;
- if the absolute target is already present on retry, verify it without applying
  another delta;
- every planned mutation must be `APPLIED_VERIFIED` before session confirmation
  advances;
- technical apply/verification failures remain technical outcomes and must not
  be converted into photographic REVIEW merely to converge the session.

A non-converged confirmed pass ends at `RERENDER_REQUIRED`. A later pass is
created only by `Prepare Next AI Package`, after the render freshness barrier
accepts a new generation.

## Non-Negotiable Safety Boundaries

- Never open or modify `.lrcat`, `.lrcat-wal` or `.lrcat-shm` directly.
- Never write to `.lrdata`.
- Never modify RAW/NEF/JPEG originals or EXIF capture fields.
- Canonical iterative mutation is limited to Catalog `Exposure2012`.
- Never modify White Balance, Contrast, Highlights, Shadows, Whites, Blacks,
  Clarity, Texture, Vibrance, Saturation, Crop, Straighten, Masks, Keywords,
  Rating, Label, Sharpening, Noise Reduction or export settings.
- External AI never receives Lightroom/Catalog/cache mutation authority.
- Never delete or move user photographs.
- Final export remains manual.
- Never store credentials/API keys in tracked files.
- Runtime sessions, previews, decisions, logs, backups, temp files and secrets
  must not be committed.

Legacy XMP transaction code retains its own safety contract in
`docs/XMP_SAFETY.md`; do not expand or substitute it for the canonical Catalog
route without explicit owner/architecture authority.

## Session and Pass Integrity

- One session freezes its source-folder scope and image identities.
- Each pass has monotonic `pass_number`, unique `pass_id` and `parent_pass_id`.
- Every pass owns its selection, manifest, Lightroom-rendered previews, contact
  sheets/index, task, bundled skills, decision schema, decisions and evidence.
- Missing required package/session identity or immutable inputs fails closed.
- External AI may write only the authorized current-pass decision output.
- Apply must use exact session/pass/source-folder lineage.
- A confirmed pass is never silently re-applied.
- A later pass is never prepared implicitly by Import/Apply.
- Stale/unproven render evidence must not advance the next pass.

## AI Decision Scope

Every captured target pass bundles the canonical visual skills needed by the
current contract, but `docs/AI_JUDGE_CONTRACT.md` defines the active MVP scope.

For the current exposure-only MVP, AI must:

- read the bundled task/skills and manifest;
- inspect contact sheets first for batch context/relative exposure, then
  individual previews when needed;
- identify intended subject/person priority and legitimate scene atmosphere;
- judge exposure consistency, reference relationship and meaningful outliers;
- return exactly one grounded PASS / ADJUST / REVIEW decision per in-scope
  preview;
- use zero delta for PASS/REVIEW and a finite bounded proposal for ADJUST;
- never invent identities, paths, objects or scene details.

The current small-preview task must **not** perform culling or judge blur,
focus, sharpness, image damage, relevance or duplicates. Preserved legacy
quality/relevance skills do not activate those features in the MVP.

AI output is untrusted input until schema, exact-set identity, lineage,
immutable package evidence and preview byte/SHA validation pass.

## Execution Rules

1. **Classify task** — identify scope, risk, affected capability, allowed files,
   forbidden files and proof before editing.
2. **Define done first** — record terminal evidence before implementation.
3. **Use bounded evidence** — targeted search/read first; reuse unchanged
   same-thread preflight and use delta checks when repository truth is stable.
4. **Choose one recommendation** — do not push routine technical decisions back
   to the owner.
5. **Make the smallest complete change** authorized by the active Work Order.
6. **Verify by execution** — run focused/full/integration/syntax/diff/status
   checks required by the task; reports alone are not proof.
7. **Reconcile truth at closeout** — capability/status/evidence/roadmap/current
   Work Order must agree before declaring completion.

## Anti-Loop Work Order Policy

A new failure does not automatically mean a new Work Order.

Classify the trigger first:

- defect discovered while proving the active acceptance gate → fix under the
  active Work Order when it is within the same capability/boundary;
- stale/conflicting canonical documentation → reconcile during active closeout;
- genuinely new capability, architecture boundary, safety model or explicit
  owner product requirement → may justify a new Work Order;
- post-MVP improvement → keep in `docs/ROADMAP.md` backlog until its phase is
  activated.

Before creating a new Work Order, the Controller must state:

1. the roadmap gate it advances;
2. why the active Work Order cannot safely own the work;
3. the new capability/boundary being introduced;
4. the terminal evidence that will close it.

If these are not clear, do not create another Work Order. Do not create a
separate Work Order only to reconcile documentation for the current gate.

## Common AI Failure Modes

- **Memory over repository truth** — current files, Git and executed evidence
  override prior summaries.
- **Worker report treated as proof** — inspect actual diff/evidence/state.
- **Proof chain left open** — code complete without required evidence and truth
  reconciliation is not complete.
- **Unauthorized scope expansion** — do not add unrelated refactors,
  frameworks, dependencies, features or cleanup.
- **Roadmap drift** — do not treat the newest bug/WO as the entire product plan.
- **Phantom backlog** — do not generate tasks from stale `PLANNED/BLOCKED`
  entries before reconciling them against current implementation/evidence.

## Engineering and Git Rules

- Work on one bounded active Work Order at a time.
- Do not redesign architecture outside owner/Work Order authority.
- Prefer existing dependencies and the smallest sufficient implementation.
- Add/update tests for behavior changes where testable.
- Do not use broad staging such as `git add .` in local execution workflows.
- Workers do not commit/push unless explicitly authorized.
- Do not force-push, rewrite shared history, discard owner changes or perform
  destructive resets without explicit authority.
- Never claim commit/push/PR/merge/test state that was not verified.

## Required Preflight

Before editing, establish:

- active Work Order and current roadmap gate;
- affected capability IDs and evidence maturity;
- allowed/forbidden files;
- expected behavior change and required validation;
- current HEAD and relevant Git status/dirty classification;
- dry-run vs real Lightroom mutation mode;
- exact safety boundary.

Unresolved architecture conflict, unavailable required proof, destructive action,
credentials, paid API use or unsafe Lightroom mutation without owner authority
is a stop condition.

## On-Demand Repository Intelligence

Serena and CodeGraph are optional aids, not default preflight requirements.
Use the smallest sufficient method: targeted search → bounded reads/symbol lookup
→ Serena for material semantic navigation → CodeGraph for material dependency
impact. An unused capability is `NOT_REQUIRED`, not failed. Do not retrieve the
same unchanged source through multiple mechanisms without a concrete reason.

## Dirty Worktree Classification

- `NON_BLOCKING` — identified pre-existing owner/local change is unrelated and
  can be preserved/excluded without modification.
- `BLOCKING` — dirty state overlaps task authority/proof so ownership or result
  attribution is ambiguous.
- `CRITICAL` — secrets, destructive/unauthorized mutation, corrupted safety
  evidence or user photo/Catalog/cache risk.

Never overwrite, stash, restore, stage or commit an owner change without
appropriate authority.

## Documentation and Knowledge Capture

`docs/INDEX.md` defines canonical placement. Prefer updating an existing
canonical document over creating another status/roadmap/evidence summary.

Every Work Order truthfully classifies affected documents as `UPDATED`,
`REVIEWED_NO_CHANGE`, `NOT_APPLICABLE` or `BLOCKED`.

Capture durable behavior, architecture, accepted rationale, executed validation,
known limitations and decisions that should not reopen without new evidence.
Do not record speculative narration or private reasoning.

## Status Truth

- Code existence supports at most `IMPLEMENTED`.
- Focused automated proof supports at most `TESTED`.
- Cross-component automated/integration proof supports `INTEGRATED`.
- Representative Lightroom Classic operation is required for
  `LIVE_VERIFIED`.
- A real observation may prove only part of a capability; record the remaining
  gate explicitly instead of over-promoting.
- Worker claims alone never promote status.
- Unknown evidence remains unknown; downgrade stale status when required.

## Completion Gate

A Work Order closes only when:

- its acceptance criteria are satisfied or a precise terminal stop condition is
  recorded;
- required automated/live validation is actually executed;
- diff/syntax/scope checks required by the task pass;
- forbidden/runtime/private artifacts are absent from the tracked change;
- documentation impact review is complete;
- canonical documents match implemented evidence;
- roadmap phase, capability matrix, validation register, project status, active
  Work Order and current pointer agree;
- remaining risks/post-MVP work are explicit rather than silently promoted into
  another Work Order.

## Final Report

Report only verified outcomes: active Work Order, files changed, behavior,
validation actually performed, documentation reconciliation, current status,
remaining risk/stop condition, and Git/PR/push state. Do not claim success
without executed evidence.
