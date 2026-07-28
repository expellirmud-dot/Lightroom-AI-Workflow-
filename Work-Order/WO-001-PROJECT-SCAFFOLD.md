# WO-001 — Project Scaffold and Governance Baseline

STATUS: READY

## Repository

- Local root: `D:\ai-tools\lightroom-ai-exposure`
- Remote: `https://github.com/expellirmud-dot/Lightroom-AI-Workflow-.git`
- Target platform: Windows
- Python: 3.11 or newer

## Objective

Create the initial project scaffold and the minimum governance/configuration foundation required for later Lightroom integration.

This Work Order does **not** authorize Lightroom SDK integration, Vision API calls, Catalog access, Preview-cache access, or real XMP modification.

## Product Boundary

The future product will:

1. Receive selected photographs from Lightroom Classic.
2. Use Lightroom-rendered JPEG previews that already include the current preset/develop appearance.
3. Ask a vision model to judge which photographs should have exposure increased or decreased.
4. Back up XMP sidecars.
5. Modify only `crs:Exposure2012` after explicit real-write authorization.
6. Return results for the user to read into Lightroom and review before manual export.

The MVP must remain simple. Do not add scene naming, skin metering, histogram matching, automatic deletion, or automatic final export.

## Required Preflight

Before editing:

1. Confirm the exact repository root.
2. Run `git status --short`.
3. Confirm the current branch and HEAD.
4. Stop if unexpected tracked or untracked files exist.
5. Read this entire Work Order.
6. Report the intended file scope before making changes.

## Allowed Files

Only these paths may be created or changed:

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `config/settings.json`
- `docs/ARCHITECTURE.md`
- `docs/XMP_SAFETY.md`
- `docs/AI_JUDGE_CONTRACT.md`
- `docs/DECISIONS.md`
- `src/lr_ai_exposure/__init__.py`
- `src/lr_ai_exposure/config.py`
- `src/lr_ai_exposure/models.py`
- `src/lr_ai_exposure/main.py`
- `tests/conftest.py`
- `tests/test_config.py`

Do not modify this Work Order or `Work-Order/CURRENT_WORK_ORDER.md`.

## Required Directory Shape

```text
D:\ai-tools\lightroom-ai-exposure\
├─ AGENTS.md
├─ README.md
├─ pyproject.toml
├─ .env.example
├─ .gitignore
├─ config\
│  └─ settings.json
├─ docs\
│  ├─ ARCHITECTURE.md
│  ├─ XMP_SAFETY.md
│  ├─ AI_JUDGE_CONTRACT.md
│  └─ DECISIONS.md
├─ Work-Order\
│  ├─ CURRENT_WORK_ORDER.md
│  └─ WO-001-PROJECT-SCAFFOLD.md
├─ src\
│  └─ lr_ai_exposure\
│     ├─ __init__.py
│     ├─ config.py
│     ├─ models.py
│     └─ main.py
├─ runtime\
│  ├─ jobs\
│  ├─ logs\
│  └─ temp\
└─ tests\
   ├─ conftest.py
   └─ test_config.py
```

Runtime directories may be created locally but their contents must be ignored by Git.

## Implementation Requirements

### 1. `AGENTS.md`

Create durable instructions for future coding agents. It must require this read order:

1. `AGENTS.md`
2. `docs/ARCHITECTURE.md`
3. `docs/XMP_SAFETY.md`
4. `docs/AI_JUDGE_CONTRACT.md`
5. `Work-Order/CURRENT_WORK_ORDER.md`
6. The active Work Order

It must enforce:

- One bounded Work Order at a time.
- Smallest safe change.
- No direct `.lrcat`, `.lrcat-wal`, `.lrcat-shm`, `.lrcat-data`, or `.lrdata` access in the MVP.
- No RAW/JPEG original modification.
- No secret values in tracked files.
- Default `dry_run: true`.
- Only `crs:Exposure2012` may eventually be modified.
- XMP backup before every authorized real write.
- AI output is untrusted and must be schema validated.
- No broad staging such as `git add .`.
- Worker must not commit or push unless a future Work Order explicitly authorizes it.
- Unexpected dirty files are a stop condition.

### 2. Architecture documents

`docs/ARCHITECTURE.md` must lock this canonical future flow:

```text
Lightroom selection
→ Lightroom-rendered temporary JPEG previews
→ ordered manifest.json
→ one-shot Python CLI
→ Vision AI
→ validated ai-decisions.json
→ XMP backup
→ controlled Exposure2012 apply
→ result.json
→ user reads metadata into Lightroom
→ user reviews and exports manually
```

The initial IPC decision is file handoff plus a one-shot Python CLI. Do not introduce Flask, FastAPI, a resident HTTP server, or a file watcher in this Work Order.

`docs/XMP_SAFETY.md` must state:

- Allowed property: Camera Raw namespace `crs:Exposure2012` only.
- Forbidden examples: `exif:ExposureTime`, `exif:ExposureProgram`, White Balance, Crop, Masks, Keywords, Rating, Label, Sharpening, Noise Reduction, and all unrelated metadata.
- Future calculation: `new_exposure = existing_exposure + validated_delta_ev`.
- XMP writes must use backup, temporary file, validation, and atomic replacement.
- Dry run never modifies source XMP.

`docs/AI_JUDGE_CONTRACT.md` must define an ordered input/output contract with immutable `image_id`, numeric `delta_ev`, confidence in `[0,1]`, reject suggestion, and reason. It must require exactly one decision for every input image and reject unknown or duplicate IDs.

`docs/DECISIONS.md` must record these accepted decisions:

- Separate project at `D:\ai-tools\lightroom-ai-exposure`.
- No direct Catalog or Preview-cache access in MVP.
- Lightroom plug-in will render selected previews in a later Work Order.
- File handoff plus one-shot CLI is the initial IPC.
- Only `crs:Exposure2012` may eventually be mutated.
- Default execution is dry run.
- Final export remains manual in MVP.

### 3. Python package

Use a `src` layout and package name `lr_ai_exposure`.

`pyproject.toml` must:

- Require Python `>=3.11`.
- Define a console script named `lr-ai-exposure` pointing to `lr_ai_exposure.main:main`.
- Include only dependencies actually used by this bounded scaffold.
- Include pytest configuration.

Do not add Pillow, lxml, httpx, Flask, FastAPI, Click, or an AI SDK unless the current implementation truly imports and uses it. Prefer the standard library plus `pydantic` only if it materially improves configuration validation. A zero-runtime-dependency scaffold is acceptable.

`config.py` must:

- Load JSON settings using `pathlib.Path`.
- Validate required fields and types.
- Resolve relative runtime paths against the project root or configuration file location consistently and document the rule.
- Allow environment variables to override secret-bearing AI fields without requiring secrets during dry-run configuration checks.
- Never print secret values.
- Raise clear, typed errors for malformed JSON, missing required fields, invalid EV limits, and invalid boolean values.

`models.py` must contain only data models needed by this Work Order. Do not pre-build the full future system.

`main.py` must provide:

```powershell
python -m lr_ai_exposure.main --check-config
```

The command must validate configuration, print a concise success summary without secrets, and exit `0`. Invalid configuration must print a useful error to stderr and exit non-zero.

### 4. Default configuration

`config/settings.json` must include at least:

```json
{
  "catalog_path": "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo\\ToTo.lrcat",
  "preview_cache_path": "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo\\ToTo Previews.lrdata",
  "runtime_directory": "runtime",
  "export_root": "G:\\Drive",
  "preview_size": 2048,
  "maximum_delta_ev": 1.0,
  "minimum_apply_confidence": 0.8,
  "dry_run": true,
  "ai_model": "",
  "ai_endpoint": ""
}
```

Catalog and Preview-cache paths are reference values only. This Work Order must not open them.

`.env.example` must contain placeholders only:

```dotenv
AI_API_KEY=
AI_MODEL=
AI_ENDPOINT=
```

### 5. Git ignore

Ignore at least:

- `.env`
- Python cache/build/test artifacts
- virtual environments
- `runtime/jobs/**`
- `runtime/logs/**`
- `runtime/temp/**`
- generated previews
- XMP backups
- AI result artifacts

Keep empty runtime directories only if needed through `.gitkeep`; otherwise create them at runtime later.

## Tests

Create focused tests for:

- Valid default configuration.
- Malformed JSON.
- Missing required setting.
- `maximum_delta_ev <= 0` rejection.
- Confidence outside `[0,1]` rejection.
- Invalid `preview_size` rejection.
- Environment override behavior without exposing secrets.
- `--check-config` success and failure exit behavior.

Tests must not read the real Lightroom Catalog, Preview cache, photographs, or XMP files.

## Forbidden Actions

- Do not access or modify the real Lightroom Catalog directory.
- Do not open `ToTo.lrcat` or any `.lrdata` package.
- Do not call external AI APIs.
- Do not install a Lightroom plug-in.
- Do not implement preview rendering.
- Do not implement XMP parsing or writing.
- Do not add a background service or HTTP endpoint.
- Do not implement reject marking in Lightroom.
- Do not implement export automation.
- Do not commit or push.
- Do not continue to WO-002.

## Validation

Run from the repository root using the active Python environment:

```powershell
python -m pytest -q
python -m lr_ai_exposure.main --check-config
python -m compileall -q src

git diff --check
git status --short
```

If editable installation is required to run the module, use:

```powershell
python -m pip install -e .
```

Do not install unrelated packages.

## Acceptance Criteria

- Required scaffold files exist and match the actual architecture.
- Configuration loads and validates on Windows paths.
- Missing API credentials do not block dry-run config validation.
- Config check exits `0` for the checked-in configuration.
- Invalid configurations fail clearly.
- Tests pass.
- No real Lightroom or image files are accessed.
- No file outside the allowed list changes.
- Git diff contains only WO-001 files.
- No commit and no push are performed.

## Required Final Report

Return only:

```text
WORK_ORDER: WO-001-PROJECT-SCAFFOLD
STATUS: DONE | BLOCKED
FILES_CHANGED:
- ...
VALIDATION:
- command: result
TESTS:
- passed/failed count
GIT_STATUS:
- exact concise summary
REMAINING_RISKS:
- ...
STOP_CONDITION:
- NONE or exact condition
WORKER_DONE
```

Do not claim completion without command evidence.