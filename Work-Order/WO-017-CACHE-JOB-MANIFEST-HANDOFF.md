# WO-017: Cache Preview Job Manifest Handoff

## Objective
Create a complete job contract from Lightroom selection to extracted cached previews without rendering or exporting preview JPEGs through Lightroom.

## Preconditions
- WO-016 extractor passes for a representative batch.

## Scope
- Create a unique job directory under:
  `runtime\jobs\<job_id>\`
- Write:
  - `selection.json`
  - `manifest.json`
  - `previews\`
  - `logs\`
- Ensure every manifest preview path exists.
- Preserve Lightroom selection order.
- Keep the job dry-run only.

## Manifest Requirements
Each image entry must include:
- `seq`
- `image_id`
- `raw_path`
- `xmp_path`
- `preview_path`
- cache identity fields used for mapping
- extraction status
- preview byte size
- source/cache timestamps when available

## Required Behavior
- The Lightroom plug-in writes selected-photo identity data only.
- Python snapshots the cache and extracts previews.
- Manifest is written only after successful validation.
- Partial failures are explicit and never reported as full success.
- No XMP mutation.

## Acceptance Criteria
- A 25-photo selection produces one valid job.
- Every `FOUND` manifest entry points to a readable JPEG.
- Counts reconcile: selected, found, missing, ambiguous, failed.
- Python dry-run accepts the generated manifest.
- No Lightroom preview export occurs.

## Stop Conditions
- Manifest schema conflicts with `src/lr_ai_exposure/job.py`.
- Selection order cannot be preserved.
- Preview paths cannot be validated before handoff.
- Any hidden fallback to full-resolution export.

## Validation
```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Status
BLOCKED_BY_WO_016
