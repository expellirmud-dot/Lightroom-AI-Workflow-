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
BLOCKED_BY_WO_021


