# Lightroom AI Exposure Assist

A Windows-first Lightroom Classic exposure assistant. Lightroom remains the
authoritative preset/color renderer; the application is limited to guarded
`crs:Exposure2012` changes in proprietary-RAW XMP sidecars.

## Project status

The approved target is a provider-agnostic Exposure Session with immutable
iterative passes:

```text
diagnose folder
-> capture Lightroom-rendered previews
-> group scenes and judge exposure outliers
-> apply validated Exposure2012 adjustments
-> Lightroom renders again
-> recheck until PASS/REVIEW or safe stop
```

This target is documented but **not implemented** at the current source head.
The current plug-in still contains WO-029's Prepare Current Folder / Apply
Prepared Job single-pass workflow. The plug-in loads, but the first owner-run
Prepare test stopped with zero eligible proprietary-RAW masters before Python,
preview-cache, CLI, or apply execution. Do not treat the iterative workflow or
real XMP apply as live verified.

## Next implementation seam

`DIAGNOSE_CURRENT_FOLDER` will be implemented first. It will report active
folder path, direct photo/eligibility metadata, observed Lightroom formats,
preview-cache readiness, runtime/CLI/bridge readiness, and XMP/metadata-sync
safety in one read-only diagnostic run.

No session or real apply implementation begins until that evidence is reviewed.

## Target operating principles

- Lightroom Classic is the only authoritative renderer.
- External vision AI judges subjects, scene groups, references, and exposure
  outliers through a strict file contract.
- Deterministic Python validates identity, pass lineage, convergence,
  oscillation, render freshness, authorization, and XMP safety.
- PASS and REVIEW never write XMP; only validated ADJUST may be authorized.
- Scene groups persist across passes unless conflicting evidence causes REVIEW
  or a provenance-recorded split.
- Read-only preview-cache snapshot/extraction and transactional XMP
  backup/write/verify/rollback are preserved.
- Final JPEG export remains manual in Lightroom.

See `docs/FOLDER_JOB_WORKFLOW.md`, `docs/ARCHITECTURE.md`,
`docs/DIAGNOSTIC_PREFLIGHT.md`, and `docs/XMP_SAFETY.md` for the target
contracts and current/target boundary.

## Provider strategy

The canonical AI boundary is a filesystem pass package. Codex, AntiGravity,
OpenHands, Hermes, other file-capable agents, free/local vision models, or
optional API adapters may produce the same decision schema.

No paid API, provider-specific account, API key, or `.env` file is required by
the canonical target. Existing Google/API code, dependencies, and environment
templates are legacy compatibility surfaces until a later implementation Work
Order isolates or removes them.

## Development setup

```powershell
git clone https://github.com/expellirmud-dot/Lightroom-AI-Workflow-.git
cd Lightroom-AI-Workflow-
uv run lr-ai-exposure --check-config
uv run pytest -q
```

Current configuration validation still reflects legacy source requirements;
passing it does not prove the target session/pass runtime.

## Safety boundaries

- Never modify RAW/JPEG originals or Lightroom catalog files.
- Never write to the live Lightroom preview cache.
- Modify only `crs:Exposure2012` in an existing sidecar.
- Back up and verify every authorized XMP write.
- Fail closed when metadata synchronization or a new Lightroom render
  generation cannot be proven.
- Never compound corrections from a stale or unproven preview.
- Never commit runtime sessions, previews, decisions, logs, XMP backups, or
  credentials.
