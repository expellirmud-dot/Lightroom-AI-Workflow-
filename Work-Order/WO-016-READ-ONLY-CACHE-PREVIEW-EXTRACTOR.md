# WO-016: Read-Only Lightroom Cache Preview Extractor

## Objective
Convert the proven WO-015 identity mapping into a bounded, read-only extractor that returns the cached preview for a requested Lightroom photo.

## Preconditions
- WO-015 is closed with repeatable selected-photo identity mapping.
- The mapping does not require `.lrcat` access.

## Scope
- Implement a Python cache adapter with an explicit input contract.
- Input: selected-photo identity records produced by the Lightroom plug-in.
- Output: one JPEG preview per requested photo plus structured extraction metadata.
- Read from disposable database snapshots, not live writable handles.
- Preserve deterministic ordering and deterministic output names.

## Required Behavior
- Create a snapshot directory for `previews.db` and `root-pixels.db`.
- Open SQLite snapshots read-only.
- Resolve each requested photo through the WO-015 identity chain.
- Extract the best available cached preview without upscaling.
- Write output atomically.
- Report `FOUND`, `MISSING`, `AMBIGUOUS`, or `ERROR` per image.
- Never fall back to Lightroom export in this Work Order.

## Output Naming
```text
000001__<source-stem>.jpg
000002__<source-stem>.jpg
```

## Acceptance Criteria
- Extracts the correct cached preview for at least 10 known photos.
- Ordering matches the Lightroom selection order.
- Missing or ambiguous mappings fail closed.
- No `.lrdata`, `.lrcat`, RAW, or XMP mutation occurs.
- Re-running produces the same identity-to-output mapping.

## Stop Conditions
- Mapping drift from WO-015.
- Live cache cannot be snapshotted safely.
- Preview BLOB encoding is not consistently decodable.
- Any need to modify the Lightroom cache.

## Validation
```powershell
python -m pytest -q
python -m compileall -q src
git diff --check
git status --short
```

## Status
CLOSED
