# Lightroom AI Exposure Assist

A Windows-first Lightroom Classic exposure assistant. Lightroom remains the
authoritative renderer and Catalog-visible Develop state. The canonical
iterative workflow is provider-agnostic and separates Lightroom capture/apply
from external AI execution.

## Current status

The project is in **MVP closure / Lightroom live certification**.

The explicit package/session workflow, contact-sheet pipeline and WO-039 Catalog
commit barrier are implemented and CI-certified. A representative live session
already reached a 324-image decision/apply stage, and Lightroom was later
observed holding the 21 requested absolute `Exposure2012` targets. That live run
also exposed the pre-WO-039 defect: verification occurred too early inside the
same Lightroom write callback and read stale values.

WO-039 moves verification after the write callback, bounds the polling window,
makes retry idempotent and prevents technical verification failures from being
converted into photographic REVIEW. GitHub Actions run #91 passed on Windows
Python 3.12 and 3.13.

The remaining gate is owner-operated: re-run Import/Apply on the affected
session, prove the 21 targets without a second delta, reach
`PASS=303 / REVIEW=0 / RERENDER_REQUIRED`, then prove a fresh next package after
Lightroom rerenders. Do not claim the complete iterative loop `LIVE_VERIFIED`
until that succeeds.

See `docs/ROADMAP.md` for the closure gate and post-MVP direction.

## Canonical Lightroom workflow

```text
Lightroom: Diagnose Current Folder (optional/readiness)

Lightroom: Prepare AI Package
→ capture source-folder/image identity + current Catalog Exposure2012
→ Python snapshots Previews.lrdata read-only
→ extract/validate Lightroom-rendered JPEG previews
→ build ordered 4×4 contact sheets + index
→ save immutable manifest + task + skills + schema + previews
→ remove temporary cache DB snapshots after package validation
→ PACKAGE_READY
→ plug-in exits

External AI application — separate/later
→ open the saved pass package
→ inspect contact sheets/previews under bundled task/skills
→ write exact JSON decisions into decisions/
→ exit

Lightroom: Import / Apply AI Results
→ refuse incomplete results without mutation
→ validate/freeze exact decisions
→ build absolute guarded Exposure2012 plan
→ request Exposure2012-only Catalog changes
→ verify committed values after the write callback with a bounded barrier
→ SESSION_COMPLETE or RERENDER_REQUIRED
→ plug-in exits

Lightroom: Prepare Next AI Package
→ only after prior apply confirmation and Lightroom rerender
→ render freshness barrier must prove a new generation
→ save next immutable package
→ PACKAGE_READY
→ plug-in exits
```

There is no resident AI listener, provider polling loop, browser automation or
API connection inside the Lightroom plug-in.

## What preview-cache extraction means

The AI sees JPEG previews already rendered by Lightroom after the user's current
preset/Develop baseline. Those previews live in `Previews.lrdata`, not in the
`.lrcat` file itself.

The plug-in does not query SQLite or decode `.lrdata`. It supplies stable
Lightroom identity and current Catalog `Exposure2012` to Python. Python snapshots
the preview cache read-only, maps those identities to cached previews, validates
the JPEGs, builds ordered contact sheets/index, and stores the durable evidence
in the pass package. Temporary snapshot DBs are removed after package validation.

Responsibilities remain separated:

- Lightroom plug-in: source-folder/image identity, current Catalog Exposure,
  explicit Prepare/Apply/Prepare-Next and Lightroom-observed apply confirmation.
- Python: safe preview extraction, package/session engine, validation,
  convergence/planning, render freshness and evidence.
- External AI: visual exposure judgment only.

## External AI

The canonical AI boundary is the saved pass folder. Any file-capable vision
application may be used if it follows the bundled task/schema and writes the
required decision set. It should inspect contact sheets first for relative
exposure context and open individual previews when necessary.

The current MVP task is exposure-only. Small package previews must not be used
to cull photos or judge blur, focus, sharpness, damage, relevance or duplicates.
AI provider/model quality testing is intentionally separate from the technical
MVP closure gate.

No API key is required by the Lightroom plug-in or core package/session engine.
Provider-specific automation is optional and isolated.

## Legacy commands

WO-029 single-pass Prepare/Apply commands and historical iterative/resume source
files remain for compatibility but are not the canonical workflow. Their XMP or
metadata-synchronization requirements must not be assumed for the current
Catalog-authoritative route.

## Development setup

```powershell
git clone https://github.com/expellirmud-dot/Lightroom-AI-Workflow-.git
cd Lightroom-AI-Workflow-
uv run lr-ai-exposure --check-config
uv run pytest -q
```

## Safety boundaries

- Never modify RAW/JPEG originals or Lightroom Catalog database files directly.
- Never write to the live Lightroom preview cache.
- Canonical iterative mutation may change only Catalog `Exposure2012`.
- External AI has no mutation authority.
- Import / Apply never prepares the next pass implicitly.
- Prepare commands never invoke external AI.
- Retry/recovery must use absolute-target/idempotent Catalog verification; do
  not apply a prior delta twice.
- Final JPEG export remains manual in Lightroom.
- Never commit runtime sessions, previews, decisions, logs, backups or secrets.

See `docs/FOLDER_JOB_WORKFLOW.md`, `docs/ARCHITECTURE.md`,
`docs/AI_JUDGE_CONTRACT.md`, `docs/DECISIONS.md`, `docs/CAPABILITY_MATRIX.md` and
`docs/VALIDATION_REGISTER.md` for canonical contracts/evidence.
