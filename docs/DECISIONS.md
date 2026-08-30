# Accepted Decisions - Lightroom AI Exposure Assist

## Approved target architecture

- The canonical target is a provider-agnostic Exposure Session composed of
  immutable iterative passes.
- Lightroom Classic is the authoritative renderer. The system does not replace
  Lightroom's preset, color, or rendering engine.
- `DIAGNOSE_CURRENT_FOLDER` is the first implementation seam and aggregates all
  independently discoverable readiness problems in one run.
- External vision AI owns subject/scene/group/reference/outlier judgment and
  returns PASS, ADJUST, or REVIEW through an untrusted file contract.
- Deterministic Python owns identity, pass lineage, schema, render freshness,
  convergence, oscillation, bounds, authorization, evidence, and XMP safety.
- The Lightroom plug-in remains a thin coordinator and never hosts AI, writes
  XMP, or queries SQLite itself.

## Session and pass decisions

- Use `parent_pass_id`, not `parent_job_id`.
- Pass 1 has `parent_pass_id: null`; later passes point to the immediately
  preceding immutable pass.
- Scene groups persist by default. Contradictory evidence causes REVIEW or a
  provenance-recorded safe split, never silent regrouping.
- Later passes inspect unresolved images with stable group references.
- PASS and REVIEW are non-mutating. Only validated ADJUST may be authorized.
- The session converges when no meaningful ADJUST remains and every image is
  PASS or REVIEW.

## Pilot defaults

`0.10 EV` meaningful tolerance, `0.05 EV` quantization, `+/-1.0 EV` per pass,
`+/-2.0 EV` cumulative, and `maximum_passes = 4` are pilot defaults only.
They are policy data to calibrate with representative Lightroom evidence, not
production constants.

## Render and metadata decisions

- Render freshness requires expected Exposure2012, new pass/generation
  identity, and refreshed preview evidence/hash. Hash alone is insufficient.
- The next correction must never use an unproven or stale Lightroom preview.
- Metadata synchronization fails closed when safe catalog/sidecar state cannot
  be proven.
- The owner is asked to Save Metadata only when evidence shows that action is
  necessary; uncertainty alone does not create an unconditional ritual.

## Provider decisions

- The canonical AI boundary is a filesystem pass package.
- File-capable agents, free/local vision models, and optional API adapters write
  the same schema.
- Provider/model identity is audit metadata, not authority.
- Credentials and network dependencies belong to optional adapters and are not
  required by the core workflow.

## Preserved decisions

- exactly one active folder and direct proprietary-RAW master scope;
- sidecar-only mutation and manual final export;
- read-only Lightroom preview-cache snapshots;
- ordered identity manifests and preview byte/SHA verification;
- exact path containment and explicit two-key apply authorization;
- sequential transactional backup, temporary write, atomic replace,
  verification, rollback, and per-image checkpoint;
- runtime artifacts and secrets are never committed.

## Superseded canonical assumptions

The following remain current implementation/legacy compatibility only and are
not the approved target:

- prepare the cache once and never recapture after apply;
- one-shot/single-pass exposure correction;
- one lifetime terminal settlement per job/image;
- `SinglePassDecision` with KEEP/REVIEW/SKIP as the canonical output;
- global latest-prepared-job pointer as workflow authority;
- provider/API configuration in the core execution contract;
- fail-fast Lightroom eligibility with one generic zero-RAW error;
- preview hash alone as render freshness proof;
- any dirty Git status automatically blocking unrelated scoped work.

## Governance decisions

- Dirty paths are classified `NON_BLOCKING`, `BLOCKING`, or `CRITICAL` by
  material risk to safety, correctness, authorization, scope, or proof.
- Explicitly identified unrelated owner changes may remain untouched and
  excluded from task output.
- A completed same-thread read-first preflight is reusable while HEAD,
  authority pointer, relevant-file fingerprints, task context, and tool context
  remain unchanged.
- Subsequent steps use delta preflight; full rereads occur only after a material
  repository/context change or an explicit policy requirement.
