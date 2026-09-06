# Lightroom AI Exposure Assist

A Windows-first Lightroom Classic exposure assistant. Lightroom remains the
authoritative renderer and Catalog-visible Develop state. The canonical
iterative workflow is provider-agnostic and separates Lightroom capture/apply
from external AI execution.

## Current status

The technical Exposure-only MVP is closed. The project is in **post-MVP product improvement**.

Completed post-MVP evidence upgrades include:

- WO-040: Lightroom preview orientation correctness, LIVE_VERIFIED on a 34-image package;
- WO-042: canonical AI packages now reuse existing Lightroom-rendered cache tiers with a 1440 px minimum target (exact 1440, otherwise smallest larger tier), CAP-055 INTEGRATED;
- WO-043: root development history and documentation archive reconciliation.

The current gate is WO-041. CAP-054 is INTEGRATED and waits for Owner-operated Lightroom validation with plug-in version `1.2.11`: stale adjusted previews must wait without becoming photographic REVIEW, the next accepted pass must re-audit the complete frozen image set, and `SESSION_COMPLETE` must mean every image is PASS.

See `docs/ROADMAP.md` for the current gate and post-MVP direction. For a chronological record of which Work Order introduced each capability, see root `DEVELOPMENT_HISTORY.md`. Superseded duplicate notes are preserved under `archive/legacy-docs/` and are non-authoritative.

## Canonical Lightroom workflow

```text
Lightroom: Diagnose Current Folder (optional/readiness)

Lightroom: Prepare AI Package
→ capture source-folder/image identity + current Catalog Exposure2012
→ Python snapshots Previews.lrdata read-only
→ reuse/validate an existing Lightroom-rendered 1440-or-larger cache tier
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
Lightroom identity and current Catalog `Exposure2012` to Python. Python snapshots the preview-cache identity databases read-only, resolves UUID + digest + orientation, and reuses an existing Lightroom-rendered cache tier at or above `preview_size` (1440 px target). Exact 1440 wins; otherwise the smallest existing larger tier is used. A smaller-only cache returns `PREVIEW_TIER_NOT_READY` rather than silently feeding AI the old ~320 px RootPixels image. Python then validates the package JPEGs, builds ordered contact sheets/index, and stores durable source-tier/hash evidence in the pass package. Temporary snapshot DBs are removed after package validation.

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
