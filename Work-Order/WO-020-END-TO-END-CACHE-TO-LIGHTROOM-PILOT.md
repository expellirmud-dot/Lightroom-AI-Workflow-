# WO-020: End-to-End Cache-to-Lightroom Pilot

## Objective
Validate the complete workflow on a small copied-photo batch, from Lightroom selection through cached-preview analysis to guarded XMP exposure updates.

## Preconditions
- WO-015 through WO-019 are closed.
- Rollback has been proven.
- Owner authorizes a bounded live pilot.

## Pilot Size
- Minimum: 5 copied test photos
- Maximum: 25 copied test photos

## End-to-End Flow
```text
Lightroom selection
→ selected-photo identity handoff
→ read-only cache snapshot
→ cached preview extraction
→ manifest validation
→ single-pass AI triage and exposure judgment
→ Owner-approved apply set
→ guarded XMP Exposure2012 write
→ Lightroom metadata refresh
→ visual verification
```

## Required Evidence
- Selected count
- Cache mapping/extraction count
- AI decision count
- Applied count
- Review/skip count
- XMP before/after
- Backup and rollback evidence
- Lightroom visual verification
- Runtime duration and failure summary

## Acceptance Criteria
- No Lightroom preview export is performed.
- Cached previews map correctly for the full pilot set.
- AI analysis uses one preview per image.
- Only approved `KEEP` images are updated.
- Final visual exposure is acceptable and batch-consistent.
- Rollback remains available for every changed XMP.
- No RAW, `.lrcat`, or cache mutation occurs.

## Stop Conditions
- Any incorrect photo-to-preview mapping.
- Any incorrect XMP target.
- Any unexpected property mutation.
- Cache snapshot/read instability.
- Material visual inconsistency.
- Owner decision required.

## Validation
```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Status
ANALYZE_ONLY_PILOT_COMPLETED

## Closeout Evidence (WO-020 ANALYZE_ONLY pilot)

Executed 2026-07-28. Google API quota blocked; manual_app provider used
with Gemini 3.1 Pro High producing one strict SinglePassDecision per
canonical image.

### Environment
- `env -u PYTHONPATH -u PYTHONHOME uv run` (project .venv, CPython 3.13)
- Provider: `manual_app` (Google quota exhausted)
- Mode: ANALYZE_ONLY, apply_authorized=False, xmp_mutation=False

### Command sequence (one clean run)
1. `uv run pytest -q tests/`  → TESTS_EXIT=0
2. `uv run python scratch/prepare_wo020_canonical.py` → CANONICAL_IMAGES=5
3. `uv run python scratch/run_wo020_pilot.py` → MANUAL_RESPONSES=5,
   VALIDATED_DECISIONS=5, AI_DECISIONS_JSON_WRITTEN=YES

### Results
- 5 manifest entries (LR_3084000 … LR_3084004)
- 5 canonical Lightroom cached JPEGs extracted (id_local 3084000.0–3084004.0)
- 5 canonical UUIDs, 5 byte counts, 5 SHA-256 values preserved
- 5 manual response files (one per id_local)
- 5 validated SinglePassDecision records (schema-enforced)
- Decision ordering matches manifest ordering
- No duplicate image_id, no unknown image_id
- apply_authorized=False → no call to apply_exposure_deltas
- No RAW / XMP / catalog / preview-cache database mutation
  (only read-only snapshot + JPEG extraction into scratch, which is git-ignored)

### Decisions
- LR_3084000: +0.3 EV (highlight_risk + shadow_risk flagged; rug near clip,
  face shadow crushed) — KEEP with conservative lift
- LR_3084001 … LR_3084004: +0.0 EV — well-exposed, KEEP

### Remaining (out of scope for ANALYZE_ONLY)
- REAL_XMP_APPLY = NOT_AUTHORIZED (WO-020 pilot stops before XMP write)
- Lightroom metadata refresh and visual verification deferred to a later
  authorized apply Work Order.


