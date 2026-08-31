# Lightroom AI Exposure Assist

A Windows-first Lightroom Classic exposure assistant. Lightroom remains the authoritative renderer. The iterative workflow is provider-agnostic and separates Lightroom capture/apply from external AI execution.

## Current status

The session/pass runtime has automated evidence through WO-034..036. WO-037 changes the plug-in workflow so the AI boundary is a durable package on disk instead of a generic wait/resume loop.

Representative Lightroom Classic end-to-end evidence is still pending. Do not treat the current iterative path as `LIVE_VERIFIED` until the bounded Lightroom test is completed.

## Canonical Lightroom workflow

```text
Lightroom: Diagnose Current Folder

Lightroom: Prepare AI Package
-> capture active-folder identities + current Catalog Exposure2012
-> Python reads a validated read-only snapshot of Previews.lrdata
-> extract Lightroom-rendered JPEG previews
-> validate previews and build ordered 4×4 contact sheets + index
-> save manifest + task + skills + schema + previews
-> remove temporary cache DB snapshots after package validation
-> PACKAGE_READY
-> plug-in exits

External AI application — run separately/later
-> open the saved pass package
-> inspect previews under the bundled task/skills
-> write JSON decisions into decisions/
-> exit

Lightroom: Import / Apply AI Results
-> refuse incomplete results without mutation
-> validate/freeze exact decisions
-> build guarded Exposure2012-only plan
-> apply and verify in Lightroom
-> SESSION_COMPLETE or RERENDER_REQUIRED
-> plug-in exits

Lightroom: Prepare Next AI Package
-> use only after the prior pass is verified and Lightroom has rerendered
-> existing render barrier must pass
-> save next immutable package
-> PACKAGE_READY
-> plug-in exits
```

There is no resident AI listener, polling loop, browser automation or API connection inside the Lightroom plug-in.

## What “preview cache extraction” means

The AI sees JPEG previews already rendered by Lightroom after the user's current preset/Develop baseline. Those previews live in the Lightroom preview cache (`Previews.lrdata`), not in the `.lrcat` file itself.

The plug-in does not query SQLite and does not decode `.lrdata`. It supplies stable Lightroom identity and current Exposure2012 to Python. Python then snapshots the configured preview cache read-only, maps those identities to cached previews, validates the JPEGs, builds ordered 4×4 contact sheets plus an index, and stores those artifacts in the pass package. The temporary snapshot DBs are removed only after package validation succeeds.

This keeps responsibilities separate:

- Lightroom plug-in: which folder/images and current Catalog Exposure2012.
- Python: safe preview-cache snapshot/extraction and package/session logic.
- External AI: visual judgment only.
- Lightroom apply bridge: validated Exposure2012-only mutation and observed confirmation.

## External AI

The canonical AI boundary is the saved pass folder. Any file-capable vision application can be used later as long as it reads the bundled task/skills and writes the required JSON decisions. It should inspect prepared contact sheets first for context and relative brightness, opening individual previews only when necessary. The current MVP task is exposure-only; it must not cull photos or assess blur, focus, sharpness, damage, duplicates, or relevance from small previews.

No API key is required by the Lightroom plug-in or package/session engine. Provider-specific automation is optional and separate.

## Legacy commands

WO-029 single-pass Prepare/Apply commands remain available temporarily and are labeled `Legacy Single Pass` in the plug-in menu. Older iterative Resume implementation files are retained for compatibility but are not registered as the canonical WO-037 workflow.

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
- The WO-037 iterative Catalog apply path may modify only `Exposure2012`.
- External AI has no mutation authority.
- Import / Apply never prepares a next pass implicitly.
- Prepare commands never invoke external AI.
- Final JPEG export remains manual in Lightroom.
- Never commit runtime sessions, previews, decisions, logs, backups or credentials.

See `docs/FOLDER_JOB_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/AI_JUDGE_CONTRACT.md`, and `docs/DECISIONS.md` for canonical contracts.
