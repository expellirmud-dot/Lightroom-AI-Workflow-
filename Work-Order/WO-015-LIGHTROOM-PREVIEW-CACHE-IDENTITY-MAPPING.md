# WO-015: Lightroom Preview Cache Identity Mapping

## Objective
Prove that one known Lightroom photo can be mapped deterministically to the correct cached preview stored inside `ToTo Previews.lrdata`.

## Required Read Order
1. `AGENTS.md`
2. `docs/INDEX.md`
3. `Work-Order/CURRENT_WORK_ORDER.md`
4. `Work-Order/WO-014-POC-LRDATA-EXTRACTION.md`
5. This Work Order

## Authority
This Work Order authorizes read-only inspection of:

- `C:\Users\Expellirmud\Pictures\LR\ToTo\ToTo Previews.lrdata\previews.db`
- `C:\Users\Expellirmud\Pictures\LR\ToTo\ToTo Previews.lrdata\root-pixels.db`
- disposable copies of those databases under `scratch\`

It does not authorize modification of `.lrdata`, `.lrcat`, RAW, XMP, or catalog metadata.

## Scope
- Select one known test photo in Lightroom.
- Obtain a stable identity for the selected photo through the Lightroom SDK.
- Inspect the preview-cache schema.
- Determine the mapping chain from Lightroom photo identity to cached preview UUID/root-pixel row.
- Extract exactly one matching JPEG.
- Verify visually and by filename/path evidence that the extracted preview belongs to the selected photo.

## Required Implementation
- Add a Lightroom SDK probe that records the selected photo's available stable metadata, including path, local identifier, UUID-like metadata, and any preview-related identifier exposed by the SDK.
- Add a read-only Python mapping probe against copied SQLite databases.
- Use SQLite read-only mode where practical.
- Do not use `LIMIT 1` as mapping evidence.
- Record the exact SQL queries and mapping keys used.
- Keep generated databases, JPEGs, and logs under `scratch\`; do not commit them.

## Acceptance Criteria
- A selected known photo maps to exactly one cached preview record.
- The extracted JPEG is visually confirmed as the selected photo.
- The mapping is repeatable in a second run.
- No cache, catalog, RAW, or XMP file is modified.
- Evidence documents the complete identity chain.

## Stop Conditions
- Mapping requires direct `.lrcat` access.
- No stable key links Lightroom SDK identity to preview-cache records.
- Multiple unresolved cache records match the same selected photo.
- SQLite lock or integrity risk prevents safe read-only inspection.
- Cache schema behavior cannot be reproduced.

## Validation
```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Deliverables
- Mapping probe code
- Focused tests
- Evidence note describing the identity chain
- Updated traceability
- No committed cache databases or extracted images

## Status
ACTIVE
