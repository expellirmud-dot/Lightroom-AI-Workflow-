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

4. **Remediation & Two-Run Evidence:**
   The `cache_probe.py` was refactored to enforce exact cardinality by querying all matching UUID rows for `imageId`. It correctly returns `MISSING` (0), `FOUND` (1), or `AMBIGUOUS` (>1).
   We executed the extraction twice for `id_local = 3084734.0`:
   - **Run 1:**
     - UUID: `D6DFFE77-4C3A-4B4B-85CE-0CBB9FBB4A38`
     - JPEG Byte Length: `22829` bytes
     - SHA-256: `470f1da2cb11dc2fb39778b675f53aadb4659b8461990009ca81534ae78440c8`
   - **Run 2:**
     - UUID: `D6DFFE77-4C3A-4B4B-85CE-0CBB9FBB4A38`
     - JPEG Byte Length: `22829` bytes
     - SHA-256: `470f1da2cb11dc2fb39778b675f53aadb4659b8461990009ca81534ae78440c8`
   Both runs returned the exact same UUID and byte-for-byte matching SHA-256.

5. **Visual Confirmation & Boundaries:**
   The extracted image is visually confirmed as the selected Lightroom photo. The Python probe uses `?mode=ro` in the SQLite URI to enforce strict read-only access. No `.lrcat` or `.lrdata` mutations occur. The identity chain is stable and deterministic.

## Validation Results
- Pytest suite (`test_cache_probe.py`) passed successfully covering zero, one, multiple rows, missing JPEGs, and valid extraction.
- Execution on real cache databases succeeded twice with identical outputs.
- No forbidden files were modified.


## Conclusion
The identity chain `id_local -> ImageCacheEntry.uuid -> RootPixels.jpegData` is proven and satisfies WO-015.
