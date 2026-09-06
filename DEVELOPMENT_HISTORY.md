# Development History — Lightroom AI Exposure Assist

This file is the human-readable development ledger for the project: which Work Order introduced which capability, why it existed, and what later work superseded it.

It is **history, not current execution authority**. For current truth, read in this order:

1. `Work-Order/CURRENT_WORK_ORDER.md`
2. the active/parked Work Order named there
3. `AGENTS.md`
4. `docs/PROJECT_STATUS.md`
5. `docs/CAPABILITY_MATRIX.md`
6. `docs/VALIDATION_REGISTER.md`
7. `docs/DECISIONS.md` and architecture/workflow documents
8. Git HEAD / implementation / executed evidence

Older Work Order files sometimes retain the status wording that was true when they were written. Do not promote or reopen capability from an old header alone; the capability/evidence registers and current repository state are authoritative.

## Stable product direction

The project evolved from a small XMP-oriented proof of concept into a Windows-first Lightroom Classic Exposure assistant with these durable boundaries:

- Lightroom Classic is the authoritative renderer and Catalog-visible Develop state.
- AI performs photographic/visual Exposure judgment only.
- Python performs deterministic identity/schema/safety/evidence validation.
- Canonical mutation is guarded Catalog `Exposure2012`; external AI has no mutation authority.
- The provider-neutral filesystem package is the handoff boundary.
- RAW/JPEG originals and Lightroom database/cache files are never modified directly.

## Work Order ledger

| Work Order | Purpose / development contribution | Historical outcome / relationship to current system |
|---|---|---|
| WO-001 | Project scaffold and governance baseline | Established repository/config/test structure and initial safety conventions. |
| WO-002 | Documentation governance | Introduced maintained-document discipline and authority expectations; later governance work reconciled and strengthened it. |
| WO-003 | Project traceability registers | Added traceability/status/evidence registers that evolved into the current capability/validation/status model. |
| WO-004 — Lightroom Plugin Bridge | Early Lightroom-to-Python bridge/job runtime | Established initial host-to-Python handoff concepts; later canonical package/session commands superseded the early route. |
| WO-004 — Project Read-First Skill | Repository-truth preflight discipline | Added the read-first execution skill so implementation work begins from repository authority rather than memory. |
| WO-005 | Job and Manifest Foundation | Added bounded job directories, ordered manifests, identity/path validation, and deterministic package structure. |
| WO-006 | Lightroom Plugin Skeleton | Added the initial Lightroom Classic plug-in registration/menu/runtime skeleton. |
| WO-007 | Preview Export and Manifest Handoff | Connected Lightroom photo identity/selection with preview/manifests; later cache extraction replaced Lightroom-side preview export. |
| WO-008 | Preview Validation | Added JPEG/byte/integrity checks so invalid visual evidence fails safely. |
| WO-009 | AI Decision Contract and Mock Judge | Introduced strict structured AI decisions, exposure bounds, deterministic mock judgment, and validation. |
| WO-010 | XMP Read and Backup | Added safe XMP reading/backup foundations for the historical sidecar mutation path. |
| WO-010.1 | Exposure Judgment and Batch Consistency | Added subject/scene Exposure guidance and batch consistency concepts; later WO-041 changed this from anchor-first procedure to outcome-based scene truth. |
| WO-010.2 | Image Relevance and Quality Triage | Explored relevance/quality triage. This scope is now deferred; the current product is Exposure-only and forbids small-preview culling/focus judgment. |
| WO-011 | Exposure2012 Safe Write | Added guarded XMP `crs:Exposure2012` write behavior; retained only as legacy compatibility after Catalog-authoritative architecture. |
| WO-012 | End-to-End Dry-Run Integration | Integrated early selection → judgment → evidence/apply planning without committing real changes. |
| WO-013 | Lightroom Live Pilot | Defined the first real Lightroom pilot gate; later live-certification Work Orders superseded the original pilot shape. |
| WO-014 | LRDATA Extraction POC | Proved Lightroom preview-cache data could be investigated/extracted read-only and opened the cache-based architecture path. |
| WO-015 | Lightroom Preview Cache Identity Mapping | Proved deterministic `id_local → ImageCacheEntry → preview UUID → cached JPEG` mapping against real Lightroom cache data. |
| WO-016 | Read-Only Cache Preview Extractor | Turned identity mapping into a bounded batch extractor using read-only cache snapshots. |
| WO-017 | Cache Job Manifest Handoff | Connected Lightroom selection, cache extraction, ordered previews, and manifest/job creation. |
| WO-018 | Single-Pass AI Triage and Exposure | Unified the historical one-pass visual decision path. Relevance/quality parts are now deferred; Exposure contract survives in evolved form. |
| WO-019 | Guarded XMP Exposure Apply Pilot | Proved bounded sidecar Exposure apply with backup/rollback. This mutation path became legacy after Catalog-authoritative work. |
| WO-020 | End-to-End Cache-to-Lightroom Pilot | Integrated the WO-015…019 cache/decision/apply chain and exposed safety gaps that triggered remediation. |
| WO-021 | Vision Provider Integration Seam | Added a provider adapter seam while preserving the idea that provider identity is not core authority. |
| WO-022 | Canonical Runtime Integration Repair | Reconciled runtime components after early integration drift and restored a coherent execution path. |
| WO-023 | Manual Batch Provider & Evidence Contract | Established manual/file-based external AI as a provider-neutral evidence path with strict decision ownership. |
| WO-024 | Reproducible CLI Certification | Added reproducible CLI/test/CI certification and established a trusted automated baseline. |
| WO-025 | Transactional XMP Apply Pilot | Hardened legacy XMP mutation with transaction/backup/rollback and two-key authorization. |
| WO-026 | Lightroom Bridge & Metadata Refresh | Improved Lightroom bridge identity/metadata handling and legacy metadata refresh behavior. |
| WO-027 | Controlled Batch Expansion | Proved bounded 5→50 image expansion, checkpoint/resume isolation, and batch consistency behavior. |
| WO-028 | Real Lightroom Analyze-Only Certification | Proved real Lightroom selection → cache preview → decision import plumbing without mutation. |
| WO-028-HOTFIX | Replace unavailable `LrJson` dependency | Repaired a Lightroom SDK compatibility failure by using the project-local JSON module. |
| WO-029 | Canonical Prepared Folder Job Lifecycle | Built a durable prepare/process/apply folder-job lifecycle. It remains a legacy single-pass compatibility route after the iterative session architecture. |
| WO-030 | Exposure Session Documentation Reconciliation | Defined the target iterative Exposure Session architecture, render barrier, convergence model, and roadmap language. |
| WO-031 | Diagnose Current Lightroom Folder | Added a read-only diagnostic command/report for current-folder/cache/bridge readiness. Some old XMP-oriented aggregate semantics remain non-blocking debt. |
| WO-032 | Whole-Folder Batch & Iterative Schema | Expanded whole-folder enumeration, scene/reference state, and iterative session schema. |
| WO-033 | On-Demand Repository Intelligence Governance | Formalized risk-classified preflight and made Serena/CodeGraph optional/on-demand rather than mandatory blockers. |
| WO-034 | Catalog Exposure Runtime Hardening | Shifted canonical iteration to Lightroom Catalog `Exposure2012` targets, deterministic convergence/render barriers, and no direct Catalog DB access. |
| WO-035 | Durable AI Handoff Workflow | Made AI handoff pause/resume durable across filesystem/session artifacts rather than requiring a resident AI connection. |
| WO-036 | Lightroom Live-Test Harness | Added deterministic live-test seeders/harness support for bounded Lightroom validation. |
| WO-037 | Decoupled AI Package Workflow | Established the canonical explicit flow: Prepare Package → external AI later → Import/Apply → Prepare Next. Removed the need for a resident listener/provider loop. |
| WO-038 | Contact Sheet Package Pipeline | Added ordered 4×4 contact sheets/index and package integrity so AI can judge batch/scene context efficiently. |
| WO-039 | Catalog Apply Commit Barrier & Recovery | Fixed same-callback stale Develop reads, moved verification post-commit, added bounded/idempotent confirmation, and live-closed the technical MVP. |
| WO-040 | Preview Orientation Correctness | Fixed sideways portrait AI evidence by reading Lightroom orientation codes, preserving source render fingerprints, and normalizing only package artifacts; live-verified 34/34 images. |
| WO-041 | Scene-Complete Exposure Judgment & Iteration Safety | Changed PASS to “evaluated/no change,” added explicit absolute scene verdicts, re-audits the complete frozen set, makes stale rerenders WAIT instead of REVIEW, and requires all-PASS for completion. CAP-054 is INTEGRATED and awaits Owner live Lightroom validation with plug-in 1.2.11. |
| WO-042 | Standard Preview Cache Reuse | Replaced canonical ~320 px RootPixels AI evidence with already-rendered Lightroom cache tiers: exact 1440 preferred, otherwise smallest larger tier; no render/cache write. Real 34-image package proof reused 1920 tiers. CAP-055 INTEGRATED. |
| WO-043 | Development History & Documentation Archive | Added this root ledger and consolidated clearly superseded duplicate notes/roadmaps into `archive/legacy-docs/` without deleting historical evidence. |

## Major architecture phases

### Phase 1 — Foundation and safety (WO-001…013)

The project established repository governance, job/manifest structure, Lightroom plug-in plumbing, preview validation, AI decision contracts, XMP safety, and early dry/live pilots.

### Phase 2 — Read-only Lightroom cache workflow (WO-014…020)

The project proved that Lightroom preview-cache evidence could be mapped and extracted deterministically without writing `.lrdata`. The first end-to-end cache/XMP chain also revealed safety/architecture gaps that were remediated before further expansion.

### Phase 3 — Provider/evidence and reproducibility hardening (WO-021…029)

The system separated provider transport from core decision authority, added manual/file-based AI handoff, reproducible CLI/CI certification, controlled batch expansion, real Lightroom analyze-only proof, and a durable prepared-folder lifecycle.

### Phase 4 — Catalog-authoritative iterative architecture (WO-030…039)

The project moved from sidecar-centered thinking to a provider-neutral Exposure Session with immutable passes, current-folder diagnostics, whole-folder state, Catalog `Exposure2012` apply, render freshness, explicit package handoff, contact sheets, and a post-commit verification barrier. WO-039 provided the technical-MVP live closure.

### Phase 5 — Post-MVP visual correctness and product quality (WO-040 onward)

WO-040 fixed preview orientation, WO-041 hardened scene-complete judgment/iteration semantics, WO-042 upgraded the AI evidence source to existing Standard Preview-class cache tiers, and WO-043 organized the project history/documentation. The next live gate remains WO-041 Owner validation before broader UX/packaging work.

## Historical archive

Clearly superseded duplicate notes/plans are kept under `archive/legacy-docs/`. They are preserved for archaeology only and do not override current architecture, capability, status, validation, or Work Order authority.

Detailed Work Orders remain under `Work-Order/`; executed evidence is normalized in `docs/VALIDATION_REGISTER.md`; current maturity is normalized in `docs/CAPABILITY_MATRIX.md`.
