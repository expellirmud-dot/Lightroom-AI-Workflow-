# Accepted Decisions — Lightroom AI Exposure Assist

## Approved target architecture

- The canonical target is a provider-agnostic Exposure Session composed of
  immutable iterative passes.
- Lightroom Classic is the authoritative renderer and authoritative visible
  Catalog `Exposure2012` state for the canonical iterative route.
- External vision AI owns photographic/semantic judgment and writes untrusted
  decision JSON only.
- Deterministic Python owns preview-cache extraction, identity/schema
  validation, pass lineage, render freshness, convergence, bounds and planning.
- The Lightroom plug-in owns Lightroom identity capture plus explicit
  Prepare / Import-Apply / Prepare-Next commands.
- The durable session/pass directory is the IPC boundary between Lightroom,
  Python and external AI.

## WO-037 decoupling decision

The Lightroom plug-in must not remain alive waiting for AI and must not own a
resident AI connection, polling loop, browser session, provider client or API
credential.

Canonical command ownership is:

```text
Prepare AI Package
→ durable pass package
→ PACKAGE_READY
→ plug-in exits

External AI Runner
→ runs later
→ reads package
→ writes decisions only
→ exits

Import / Apply AI Results
→ validate/freeze exact decisions
→ guarded Catalog Exposure2012 apply + Lightroom verification
→ SESSION_COMPLETE or RERENDER_REQUIRED
→ plug-in exits

Prepare Next AI Package
→ explicit command after rerender
→ next immutable pass
→ PACKAGE_READY
→ plug-in exits
```

A generic Resume command is not canonical because it mixes result import,
mutation, rerender boundary and next-pass capture. Legacy iterative/resume and
WO-029 single-pass surfaces may remain for compatibility but are not project
direction.

## Preview-cache and package decisions

- Lightroom supplies identity and current Catalog `Exposure2012`.
- Python owns `Previews.lrdata` snapshot/mapping/JPEG extraction; cache access is
  read-only through validated snapshots.
- Python never infers pass scope from cache contents alone.
- Extracted JPEGs are Lightroom-rendered evidence, not replacement renderings.
- Python creates immutable ordered 4×4 contact sheets/index from validated
  previews before external AI handoff.
- The current RootPixels extractor remains the selected source; the authorized
  forensic check found only the 320px JPEG payload in those snapshots.
- Contact sheets are context-first exposure input. The current MVP must not use
  the small previews for culling, blur/focus/sharpness/relevance decisions.
- Temporary cache DB snapshots are deleted only after package validation;
  manifest and package evidence remain.

## Session and pass decisions

- Use `parent_pass_id`, not `parent_job_id`.
- Pass 1 is created only by `Prepare AI Package`.
- A later pass is created only by `Prepare Next AI Package`.
- `Import / Apply AI Results` never creates another pass implicitly.
- A confirmed pass is never silently re-applied.
- PASS and REVIEW are non-mutating. Only validated ADJUST enters apply planning.

## Catalog mutation decision

The canonical iterative route is Catalog-authoritative:

- read current Catalog `Exposure2012`;
- compare it with the expected pre-apply value;
- apply only `{ Exposure2012 = absolute_target }`;
- require Lightroom-observed `APPLIED_VERIFIED` evidence before session state
  advances;
- do not require an XMP Save/Read Metadata ritual for the iterative Catalog
  route.

Legacy transactional XMP capabilities remain preserved outside the canonical
iterative route and must not be confused with current session mutation.

## WO-039 post-commit verification decision

Real Lightroom evidence showed that `getDevelopSettings()` can remain stale
inside the same `withWriteAccessDo()` callback after `applyDevelopSettings()`.
Therefore:

- the write callback validates the precondition and requests the absolute
  `Exposure2012` target only;
- verification occurs after the callback returns;
- verification uses bounded polling and must never become a resident listener;
- retry is idempotent: an already-present absolute target is verified without
  applying another delta;
- session confirmation is fail-closed and batch-atomic for the planned apply
  set;
- a technical verification failure remains technical evidence and is never
  converted into photographic REVIEW merely to settle/converge the session;
- recovery of the pre-WO-039 live session is limited to IDs recorded in its own
  failed apply evidence.

## Render decision

- A non-converged confirmed pass ends at `RERENDER_REQUIRED`.
- Apply never prepares the next pass implicitly.
- `Prepare Next AI Package` is the explicit render-generation boundary.
- The render barrier must reject stale/unproven previews before a new pass is
  admitted.

## Provider decisions

- The canonical AI boundary is a filesystem pass package.
- File-capable agents, free/local vision models, desktop/web apps and optional
  API adapters may produce the same decision contract.
- Provider/model identity is evidence metadata, not authority.
- Credentials/network dependencies belong only to optional adapters.
- No API key is required by the Lightroom plug-in or package/session core.
- Model/provider quality is a separate post-MVP evidence problem, not a reason
  to redesign the core Lightroom/package boundary.

## Preserved safety decisions

- exactly one active Lightroom source folder per session;
- no direct `.lrcat`, `.lrcat-wal` or `.lrcat-shm` access;
- no `.lrdata` writes;
- no RAW/JPEG original mutation;
- ordered identity manifests and preview byte/SHA verification;
- external AI has no mutation authority;
- only Catalog `Exposure2012` is writable in the canonical iterative route;
- final export remains manual;
- runtime artifacts and credentials are never committed.

## Deferred decisions

The following remain independent post-MVP work unless new evidence makes them
necessary for closure:

- AI model/provider quality and calibration;
- broader image quality/relevance/culling behavior;
- provider-specific transport automation;
- release packaging and UX polish beyond current technical closure.

## Governance and Work Order decisions

- Dirty paths are classified `NON_BLOCKING`, `BLOCKING`, or `CRITICAL` by
  material risk.
- A completed same-thread read-first preflight may be reused while authority and
  relevant repository fingerprints remain unchanged.
- Serena/CodeGraph are on-demand rather than mandatory preflight gates.
- Project Truth is not Task Truth: Work Order history does not redefine the
  product mission or create future requirements automatically.
- A defect discovered while proving an active acceptance gate defaults to
  remediation under the active Work Order.
- A stale/conflicting canonical document defaults to closeout reconciliation,
  not a new documentation Work Order.
- A new Work Order requires a genuinely new capability, architecture/safety
  boundary or owner product requirement, plus the roadmap gate and terminal
  evidence it advances.
- Post-MVP backlog items in `docs/ROADMAP.md` never activate themselves.
