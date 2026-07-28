# WO-004 — Lightroom Plugin Bridge and Job Directory Runtime

STATUS: ACTIVE

## Objective

Create the Lightroom Classic plugin bridge and job directory runtime
foundation. This Work Order establishes the file-handoff mechanism
between Lightroom and the Python AI project without implementing
AI judgment, XMP mutation, or catalog access.

## Required Read Order

1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. This Work Order

## Repository Root

`D:\ai-tools\lightroom-ai-exposure`

Remote: `https://github.com/expellirmud-dot/Lightroom-AI-Workflow-.git`

## Scope

### Allowed Files

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `.env.example`
- `.gitignore`
- `config/settings.json`
- `lightroom-plugin/AIExposureAssist.lrplugin/Info.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/PluginInit.lua`
- `lightroom-plugin/AIExposureAssist.lrplugin/RunExposureAssist.lua`
- `src/lr_ai_exposure/__init__.py`
- `src/lr_ai_exposure/app.py`
- `src/lr_ai_exposure/job.py`
- `src/lr_ai_exposure/lightroom_bridge.py`
- `src/lr_ai_exposure/preview_loader.py`
- `src/lr_ai_exposure/ai_judge.py`
- `src/lr_ai_exposure/xmp_editor.py`
- `src/lr_ai_exposure/reject_marker.py`
- `src/lr_ai_exposure/report.py`
- `runtime/jobs/.gitkeep`
- `runtime/logs/.gitkeep`
- `runtime/temp/.gitkeep`
- `tests/conftest.py`
- `tests/test_xmp_editor.py`
- `tests/test_job.py`
- `tests/test_ai_response.py`

Do not modify Work Order files or `CURRENT_WORK_ORDER.md`.
Do not add or modify files outside this list.

### File Layout

```text
lightroom-plugin/AIExposureAssist.lrplugin/
├── Info.lua
├── PluginInit.lua
└── RunExposureAssist.lua

src/lr_ai_exposure/
├── __init__.py
├── app.py            — orchestrator, entry point for one-shot CLI
├── job.py            — job folder creation and manifest writing
├── lightroom_bridge.py — receive manifest from plugin, return decisions
├── preview_loader.py  — prepare JPEG previews for AI consumption
├── ai_judge.py        — call Vision API, return exposure decisions
├── xmp_editor.py      — backup, read, and update Exposure2012 in XMP
├── reject_marker.py   — collect AI reject suggestions
└── report.py          — build result.json summary
```

## Implementation Requirements

### Lightroom Plugin (Lua)

The plugin runs inside Lightroom Classic. It must not contain AI
logic, XMP writing, or HTTP server code. Its only responsibility is
file handoff.

#### `Info.lua`

Minimal plugin metadata. Must declare:

- Plugin name: `AI Exposure Assist`
- LrSDK version compatibility (use `LrApplication` API level 6+ or
  the minimum version the project targets)
- Required privileges: `photo` only (no catalog write, no file system
  write beyond the designated job folder)

#### `PluginInit.lua`

Register the menu command and register a command handler that:

1. Gets the current selection from Lightroom using `LrSelection`.
2. For each selected photo, collects:
   - The photo's `photoId`
   - The RAW file path (`LrPhoto.path` or equivalent accessible property)
   - The corresponding XMP sidecar path if one exists
   - A sequential index
3. Exports a development JPEG preview for each selected photo to the
   job folder at `runtime/jobs/<job_id>/previews/` using
   `LrExportSession` or equivalent. The exported file name must be
   `{seq:06d}__{raw_file_base}.jpg` preserving selection order.
4. Writes `manifest.json` into the job folder containing one entry per
   photo with `photoId`, `rawPath`, `xmpPath`, `previewPath`, and `seq`.
5. Calls the Python backend via a one-shot subprocess or IPC mechanism
   to hand off the manifest and wait for results.
6. Writes `ai-decisions.json` and `result.json` into the job folder as
   returned by Python.
7. Logs any errors to `runtime/logs/` and records them in the run log
   within the job folder.

The plugin must not directly modify Lightroom catalog, XMP sidecars, or
photographs. All writes happen through the Python CLI or through Lightroom's
own `Read Metadata From File` / `Write Metadata To File` commands.

#### `RunExposureAssist.lua`

The command handler invoked from `Library > Plug-in Extras > AI Exposure Assist`.
It delegates to the logic implemented in `PluginInit.lua`.

### Python Backend (`src/lr_ai_exposure/`)

#### `app.py` — Orchestrator

Entry point for one-shot CLI execution:

```powershell
python -m lr_ai_exposure.app --job <job-id> --root <project-root>
```

The orchestrator must:

1. Read `manifest.json` from `runtime/jobs/<job-id>/manifest.json`.
2. Validate the manifest structure and file existence.
3. Prepare previews (delegate to `preview_loader.py`).
4. Submit previews to the AI judge (delegate to `ai_judge.py`).
5. Back up existing XMP sidecars (delegate to `xmp_editor.py`).
6. Apply validated exposure changes to XMP (delegate to `xmp_editor.py`).
7. Collect AI reject suggestions (delegate to `reject_marker.py`).
8. Generate `result.json` (delegate to `report.py`).
9. Write `ai-decisions.json` and exit.
10. Respect the `dry_run` setting from `config/settings.json` — in dry
    run mode, no XMP files are modified; all writes go to the `xmp-backup/`
    subfolder with a `.dry_run` suffix.

#### `job.py` — Job Manager

Create a uniquely named job folder under `runtime/jobs/` using the
pattern `<year>-<month>-<day>-<seq>_<YYYYMMDD_HHMMSS>`.
Example: `2569-07-24-25_20260728_130500`.

The job folder must contain:

- `manifest.json` — the ordered list of photos and their paths
- `previews/` — exported JPEG preview images
- `ai-decisions.json` — AI output (filled by app.py)
- `xmp-backup/` — backups of original XMP sidecars
- `result.json` — final summary (filled by app.py)
- `run.log` — execution log

`job.py` must provide:

- `create_job(root)` — creates folder structure, returns job path and job_id
- `write_manifest(job_path, entries)` — writes ordered manifest.json
- `write_result(job_path, result)` — writes result.json
- `write_run_log(job_path, message)` — appends to run.log

#### `lightroom_bridge.py` — Plugin IPC

Provide a function that receives a manifest (from the Lightroom plugin or a
test harness) and returns the AI decisions and result. The bridge is a
thin orchestration layer that calls `app.py`'s orchestrator logic programmatically.

```python
def process_manifest(manifest: dict, project_root: Path) -> dict:
    """Receive a manifest dict and return the combined result."""
```

No HTTP server, file watcher, or long-running process is needed for this Work
Order. The Lightroom plugin invokes Python as a one-shot subprocess.

#### `preview_loader.py` — Preview Preparation

Given a manifest entry, ensure the preview JPEG exists and is accessible to the
AI judge. The preview is exported from Lightroom by the plugin; this module:

1. Verifies each preview file exists.
2. Verifies each preview file maps back to a valid RAW file entry in the manifest.
3. Returns an ordered list of preview paths suitable for batch submission to the AI.
4. Rejects entries where the preview is missing or the RAW path does not match.

Preview filename format: `{seq:06d}__{raw_file_base_without_extension}.jpg`

Example mapping:
```
RAW: PTO_3392.NEF → Preview: 000001__PTO_3392.jpg
RAW: PTO_3393.NEF → Preview: 000002__PTO_3393.jpg
```

#### `ai_judge.py` — Vision AI Integration

Submit the batch of preview images to the configured Vision AI endpoint and return
one `ImageDecision` per image.

Input: list of preview file paths and manifest entries
Output: list of `ImageDecision` objects (defined in `models.py`)

The AI judge must:

1. Load settings from configuration (AI endpoint, model, API key source).
2. For each preview, submit the image to the Vision API with a prompt that asks
   for exposure delta and reject assessment.
3. Validate each response against the `ImageDecision` schema.
4. Clamp `delta_ev` to `[-maximum_delta_ev, +maximum_delta_ev]`.
5. Reject any decision with `confidence < minimum_apply_confidence`.
6. Return exactly one decision per input image in manifest order.

In dry_run mode, `ai_judge.py` must return deterministic mock decisions
(delta_ev=0, confidence=1.0, reject=false, reason="dry_run") for each image
instead of calling the actual AI API.

Error handling:

- API timeout: retry up to 2 times with exponential backoff, then mark as
  rejected with reason="ai_timeout" and confidence=0.0.
- Malformed response: skip that image, add error to result, continue with
  remaining images.
- No decisions returned: fail the whole job with error in result.

#### `xmp_editor.py` — XMP Sidecar Safety

Perform exactly three operations:

1. **Backup** — copy the existing XMP file to `xmp-backup/<filename>.bak`
   before any modification.
2. **Read** — parse the existing XMP and extract the current `crs:Exposure2012`
   value.
3. **Write** — apply `new_exposure = existing_exposure + validated_delta_ev` and
   write the result as the new `crs:Exposure2012` value.

Rules:

- The only property that may be changed is `crs:Exposure2012`.
- Do not modify White Balance, Contrast, Highlights, Shadows, Crop, Masks,
  Keywords, Rating, Label, Sharpening, Noise Reduction, or any other metadata.
- Do not modify EXIF camera-capture fields (`exif:ExposureTime`,
  `exif:ExposureProgram`, etc.).
- Use a temporary file and atomic replace: write to temp, validate, then rename
  over the original. If any step fails, the original XMP must remain intact.
- In dry_run mode, write the proposed change to `xmp-backup/<filename>.dry_run`
  instead of modifying the source XMP. Do not touch the source XMP at all.
- All XMP values must be parsed and written as rational numbers in the XMP
  format (`2012-1/8`). Do not convert to decimal floats in the output XMP.

Error handling:

- Missing XMP sidecar: skip the image, record error in result, continue.
- Malformed XMP: skip the image, record error in result, continue.
- Invalid Exposure2012 value: skip the image, record error in result, continue.

#### `reject_marker.py` — Reject Suggestions

Collect AI decisions where `reject=true` and summarize them for the user.

Output format for `result.json` rejections:

```json
{
  "file": "PTO_3392.NEF",
  "reason": "motion_blur",
  "confidence": 0.97
}
```

In the MVP, reject suggestions are advisory only. The Lightroom plugin does not
automatically reject or delete photos; the user reviews the suggestions manually.

Supported reject reasons (extensible):

- `motion_blur` — hand shake or subject motion
- `focus_blur` — missed focus
- `tilt` — severely tilted horizon
- `irrelevant` — not the intended subject
- `ai_error` — AI could not judge reliably
- `low_confidence` — AI confidence below threshold

#### `report.py` — Result Summary

Generate `result.json` with the following structure:

```json
{
  "job_id": "2569-07-24-25_20260728_130500",
  "total_images": 266,
  "adjusted": 218,
  "skipped": 31,
  "rejected": 17,
  "errors": 0,
  "xmp_backups": 266,
  "dry_run": true,
  "decisions": [...]
}
```

Counters:

- `total_images`: all manifest entries
- `adjusted`: images where delta_ev != 0 and confidence >= minimum_apply_confidence
- `skipped`: images where confidence < minimum_apply_confidence or delta_ev == 0
- `rejected`: images where reject=true
- `errors`: images with processing errors (missing XMP, malformed data, etc.)

### Configuration

All configuration is loaded from `config/settings.json` via `src/lr_ai_exposure/config.py`
(already implemented in WO-001). The settings used by this Work Order:

| Setting | Purpose | Required |
|---|---|---|
| `catalog_path` | Reference only; plugin reads via Lightroom SDK | no |
| `preview_cache_path` | Reference only | no |
| `working_directory` | Base for job folders | yes |
| `export_root` | Where exported previews live (set by plugin) | yes |
| `preview_size` | JPEG preview resolution | yes |
| `maximum_delta_ev` | Cap on AI exposure adjustment | yes |
| `apply_mode` | Always `"xmp"` in MVP | yes |
| `dry_run` | When true, no real XMP writes | yes |
| `ai_model` | Vision AI model identifier | no (empty = mock) |
| `ai_endpoint` | Vision AI API endpoint | no (empty = mock) |

### Tests

Create focused tests for:

- `test_xmp_editor.py`: XMP backup, parse/write Exposure2012 rational, dry_run
  mode, non-destructive on unrelated fields, atomic replace on failure.
- `test_job.py`: job folder creation, manifest write, result write, run log
  append.
- `test_ai_response.py`: AI response schema validation, delta_ev clamping,
  confidence threshold, unknown image_id rejection, duplicate detection.

All tests must run without Lightroom, without real XMP files, without network
access, and without real photographs.

## Validation

Run from repository root after implementation:

```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Acceptance Criteria

- All allowed files exist and follow the defined interfaces.
- Lightroom plugin files (Lua) are syntactically valid and follow LrSDK conventions.
- Python modules compile without errors.
- Configuration is loaded and validated correctly.
- `--check-config` exits 0 for valid configuration.
- Tests pass.
- No real Lightroom catalog, preview cache, photograph, RAW file, or XMP file
  is accessed.
- No file outside the allowed list is changed.
- Git diff contains only WO-004 files.
- No commit and no push (enforced by framework).

## Forbidden Actions

- Do not access or modify Lightroom Catalog files (`.lrcat`, `.lrcat-wal`,
  `.lrcat-shm`, `.lrdata`).
- Do not modify RAW, JPEG originals, or photographs.
- Do not modify EXIF camera-capture fields.
- Do not call external AI APIs (mock mode only).
- Do not implement XMP reading/writing beyond Exposure2012.
- Do not add database access or direct catalog manipulation.
- Do not add an HTTP server or file watcher.
- Do not implement automatic Lightroom reject or delete.
- Do not implement export automation.
- Do not commit or push.
- Do not begin WO-005.

## Final Report Format

```text
WORK_ORDER: WO-004-LIGHTROOM-PLUGIN-BRIDGE
STATUS: DONE | BLOCKED
FILES_CHANGED:
- ...
VALIDATION:
- command: result
TEST_RESULT:
- passed/failed count
GIT_STATUS:
- exact concise summary
REMAINING_RISKS:
- ...
STOP_CONDITION:
- NONE or exact condition
WORKER_DONE
```
