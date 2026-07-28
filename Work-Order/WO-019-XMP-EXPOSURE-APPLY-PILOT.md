# WO-019: Guarded XMP Exposure Apply Pilot

## Objective
Apply approved AI exposure deltas to copied test-photo XMP sidecars with full backup, validation, and rollback.

## Preconditions
- WO-018 produces validated decisions.
- Only copied test photos are used.
- Owner explicitly starts the live apply pilot.

## Scope
- Read current `crs:Exposure2012`.
- Apply only the approved signed decimal EV delta.
- Create backup before mutation.
- Write through temp file and atomic replace.
- Validate resulting XMP.
- Record before/after values and rollback path.

## Hard Boundaries
- Editable XMP property: `crs:Exposure2012` only.
- No RAW mutation.
- No `.lrcat` mutation.
- No `.lrdata` mutation.
- No other develop settings.
- No automatic apply to `REVIEW` or `SKIP`.

## Acceptance Criteria
- At least one copied test photo is updated successfully.
- Original XMP is recoverable byte-for-byte from backup.
- Only `crs:Exposure2012` changes.
- Invalid or missing XMP fails closed.
- Lightroom reflects the update after the approved metadata refresh workflow.

## Stop Conditions
- Unexpected XMP diff.
- Missing or invalid backup.
- Lightroom metadata conflict.
- Target is not a copied test photo.
- Any request to broaden editable properties.

## Validation
```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Status
CLOSED

