# WO-017 Evidence Note: Cache Preview Job Manifest Handoff

## Objective
Create a complete job contract from Lightroom selection to extracted cached previews without rendering or exporting preview JPEGs through Lightroom.

## Process and Evidence

1. **Lightroom Plugin Handoff:**
   `RunExposureAssist.lua` was rewritten to extract identity fields (`id_local`, `path`, `uuid`) and immediately write a lightweight `selection.json`. No `requestJpegThumbnail` calls are made.

2. **Manifest Schema Extension:**
   `src/lr_ai_exposure/job.py` `ManifestEntry` was extended to include:
   - `extraction_status`
   - `uuid`
   - `preview_bytes`
   The paths `raw_path`, `xmp_path`, and `preview_path` are correctly configured relative to the job directory for validation.

3. **Python Handoff Script:**
   `src/lr_ai_exposure/handoff.py` was created to bridge the plugin output and Python engine.
   - Parses `selection.json`.
   - Creates a unique `job-<timestamp>` directory in `runtime/jobs/`.
   - Copies cache databases to `cache_snapshots/`.
   - Extracts previews to `previews/`.
   - Checks that all `FOUND` previews are readable on disk.
   - Writes `manifest.json`.

4. **25-Photo Live E2E Verification:**
   `scratch/test_job_handoff.py` generated a mock `selection.json` with 25 real photo identities from the user's `ToTo Previews.lrdata`. 
   - `handoff.py` processed all 25 successfully.
   - Manifest produced contained exactly 25 entries.
   - Extraction status for all 25 was `FOUND`.
   - The job directory successfully loaded via `read_manifest()`.

## Validation Results
- Pytest `tests/test_job.py` and `tests/test_handoff.py` pass without errors.
- 25-image live cache simulation succeeds.

## Conclusion
WO-017 is complete. The job handoff pipeline accurately consumes selections and emits valid extraction manifests ready for AI triage.
