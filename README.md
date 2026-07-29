# Lightroom AI Exposure Assist

A Windows-first Lightroom Classic assistant that prepares a folder of current
Lightroom previews, lets any vision-capable AI app judge exposure, and writes
only validated `crs:Exposure2012` changes to XMP sidecars.

## How it works

1. Open the intended Lightroom folder and select all photos to process.
2. Run **Plug-in Extras → AI Exposure Assist — Prepare Selected Folder**.
3. Lightroom/Python extracts the selected previews once into
   `runtime/jobs/<job-id>/` and stops.
4. Give that job folder to AGY, Gemini CLI, Codex, or another vision AI app.
5. The AI reads `AI_TASK.md` and saves one JSON decision per FOUND image in
   the job's `decisions/` folder.
6. Optionally validate without mutation:

   ```powershell
   uv run lr-ai-exposure --process-job <job-id>
   ```

7. Run **AI Exposure Assist — Apply Prepared Job**. The program validates the
   saved decisions, backs up each approved XMP, changes only Exposure2012,
   verifies the result, and refreshes Lightroom metadata.

No Gemini API call is required by the application.

## Prepared job layout

```text
runtime/jobs/<job-id>/
├── AI_TASK.md
├── decision-schema.json
├── selection.json
├── manifest.json
├── job-state.json
├── previews/
├── decisions/
└── xmp_backups/
```

See `docs/FOLDER_JOB_WORKFLOW.md` for the complete contract.

## Setup and validation

```powershell
git clone https://github.com/expellirmud-dot/Lightroom-AI-Workflow-.git
cd Lightroom-AI-Workflow-
copy .env.example .env
uv run lr-ai-exposure --check-config
uv run pytest -q
```

## Safety boundaries

- Never modify RAW, JPEG originals, or Lightroom catalog files.
- Never write to the Lightroom preview cache.
- Modify only `crs:Exposure2012` in existing XMP sidecars.
- Back up and verify every authorized XMP write.
- REVIEW, SKIP, risky, low-confidence, missing-preview, and zero-delta images
  are not mutated.
- Final export remains manual.
