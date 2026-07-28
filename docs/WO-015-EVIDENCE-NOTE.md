# WO-015 Evidence Note: Lightroom Preview Cache Identity Mapping

## Objective
Prove selected Lightroom photo → stable identity → cache UUID → RootPixels row → exact matching JPEG.

## Process and Evidence

1. **Lightroom SDK Identity:**
   The Lightroom SDK provides the internal `id_local` (e.g., `3084734.0`) via `photo:getRawMetadata('id_local')`. We implemented `lightroom-plugin/IdentityProbe.lua` to extract this identity, along with `uuid` and `path`, and save it to a JSON file.

2. **Cache Mapping (previews.db):**
   Using the `id_local`, we performed a read-only query against `previews.db` (specifically the `ImageCacheEntry` table). We mapped `imageId = 3084734.0` to the preview UUID `D6DFFE77-4C3A-4B4B-85CE-0CBB9FBB4A38`.
   *Query:* `SELECT uuid FROM ImageCacheEntry WHERE imageId = ?;`

3. **JPEG Extraction (root-pixels.db):**
   Using the preview UUID, we performed a read-only query against `root-pixels.db` (the `RootPixels` table).
   *Query:* `SELECT jpegData FROM RootPixels WHERE uuid = ?;`
   This returned the binary BLOB of the JPEG image.

4. **Visual Confirmation:**
   The extracted BLOB was written to `scratch\extracted_preview.jpg`. The visual inspection and byte checks confirm it is a valid JPEG image matching the original Lightroom selection.

5. **Repeatability & Boundaries:**
   The Python probe (`src/lr_ai_exposure/cache_probe.py`) uses `?mode=ro` in the SQLite URI to enforce strict read-only access. No `.lrcat` or `.lrdata` mutations occur. The identity chain is stable and deterministic.

## Validation Results
- Pytest suite (`test_cache_probe.py`) passed successfully (100% coverage for the mapping logic using mock DBs).
- Execution on real cache databases succeeded without errors.
- No forbidden files were modified.

## Conclusion
The identity chain `id_local -> ImageCacheEntry.uuid -> RootPixels.jpegData` is proven and satisfies WO-015.
