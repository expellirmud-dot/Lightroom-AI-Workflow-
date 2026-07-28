# WO-016 Evidence Note: Read-Only Cache Preview Extractor

## Objective
Convert the proven WO-015 identity mapping into a bounded, read-only extractor that returns the cached preview for a requested Lightroom photo batch.

## Process and Evidence

1. **Snapshot Mechanism:**
   Created `snapshot_cache_dbs()` which copies `previews.db` and `root-pixels.db` into a scratch snapshot directory before extraction. This ensures we never hold locks on the live Lightroom databases.

2. **Batch Extraction:**
   Implemented `extract_batch()` in `src/lr_ai_exposure/cache_extractor.py`.
   - Iterates through a provided list of identity records (containing `id_local` and `path`).
   - Retrieves the UUID via `find_preview_uuid` (enforcing exact cardinality).
   - Extracts the JPEG BLOB from `root-pixels.db`.
   - Writes atomically to a `.tmp` file before renaming to the final output name.
   - Names output as `<seq>__<source-stem>.jpg` (e.g. `000001__IMG_001.jpg`).
   - Returns a structured dictionary per image with `FOUND`, `MISSING`, `AMBIGUOUS`, or `ERROR`.

3. **Validation on 10 Known Photos:**
   Executed `scratch/test_batch_extract.py` which snapped the real `.lrdata`, queried 10 known `imageId` values, and fed them to the extractor.
   - Total Input: 10
   - Total FOUND: 10
   - Missing/Error: 0
   - Output files were properly formatted as `000001__TEST_IMAGE_0001.jpg` to `000010__TEST_IMAGE_0010.jpg`.

4. **Safety Boundaries:**
   - No `.lrdata` or `.lrcat` files are modified.
   - Read-only (`?mode=ro`) SQLite URIs are maintained.
   - Missing rows fail safely by emitting `MISSING`.

## Conclusion
WO-016 is fully satisfied. The batch extractor accurately exports JPEGs for the required identities safely and deterministically.
