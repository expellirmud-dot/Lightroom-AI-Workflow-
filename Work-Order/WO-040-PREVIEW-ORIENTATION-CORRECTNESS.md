# WO-040 — Preview Orientation Correctness

STATUS: COMPLETE_LIVE_VERIFIED
ACTIVATED: 2026-09-04
CLOSED: 2026-09-04

## Trigger

Owner review of real Pass 1 package `sess-1788482026` found multiple Lightroom-rendered preview JPEGs/contact-sheet tiles displayed 90 degrees sideways even though identity, bytes and package integrity were valid. The external AI task is explicitly contact-sheet-first, so incorrect visual orientation can degrade exposure judgment.

## Roadmap outcome

Post-MVP AI judgment calibration / operator correctness: ensure the immutable visual evidence shown to external AI matches Lightroom's intended display orientation before judging exposure.

## Goal

Make package previews and derived contact sheets preserve Lightroom preview orientation deterministically without writing `.lrdata`, originals, XMP, Catalog data, or changing the exposure-only judgment scope.

## Current truth

- Canonical package extraction reads `ImageCacheEntry` + `RootPixels` from a read-only cache snapshot.
- Current extracted JPEGs contain no EXIF Orientation tag in the representative package.
- `previews.db` exposes an `ImageCacheEntry.orientation` column, but current mapping/extraction drops it.
- Read-only live evidence for the representative 34-image set shows upright records as `AB` and every visually sideways example checked as `DA`.
- Contact-sheet code currently pastes extracted JPEG pixels as-is.
- Existing package byte/SHA/order integrity does not prove visual orientation correctness.
- Render freshness currently compares `ManifestEntry.preview_sha256`; rotating/re-encoding durable previews would change that hash even if Lightroom did not rerender, so WO-040 must preserve a raw cache-render fingerprint separately from normalized visual-artifact integrity.

## Authorized scope

Implementation:
- `src/lr_ai_exposure/cache_probe.py`
- `src/lr_ai_exposure/cache_extractor.py`
- `src/lr_ai_exposure/job.py`
- `src/lr_ai_exposure/render_barrier.py`
- `src/lr_ai_exposure/session_lifecycle.py`
- `src/lr_ai_exposure/contact_sheets.py` only if required by the smallest correct design
- focused tests under `tests/test_cache_probe*.py`, `tests/test_cache_extractor*.py`, `tests/test_contact_sheets.py`, `tests/test_iterative_loop.py`, and manifest/session tests directly affected by the new raw-fingerprint field

Evidence / closeout:
- read-only inspection of the current representative `Previews.lrdata` orientation values and existing runtime package artifacts
- `Work-Order/WO-040-PREVIEW-ORIENTATION-CORRECTNESS.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `README.md` only if user workflow changes

## Forbidden

- no direct `.lrcat`/Catalog DB reads or writes
- no `.lrdata` writes
- no RAW/JPEG original or XMP mutation
- no Catalog Develop mutation
- no external AI call
- no provider-specific coupling
- no culling/quality/relevance scope expansion
- no reusing/modifying an immutable existing pass in place as production truth

## Required behavior

1. Determine orientation from the same read-only preview-cache identity record used to resolve the preview UUID.
2. Support the non-mirrored Lightroom rotation codes `AB` (0°), `BC` (90° CW), `CD` (180°), and `DA` (270° CW); mirrored/unknown values fail closed rather than being guessed.
3. Normalize only the extracted package JPEG artifact to Lightroom's intended display orientation before manifest visual-artifact byte/SHA evidence is finalized.
4. Preserve a separate SHA-256 fingerprint of the raw Lightroom root-pixel JPEG bytes before orientation normalization. Render freshness must compare this raw fingerprint, with backward-compatible fallback to historical `preview_sha256` when reading pre-WO-040 manifests.
5. Contact sheets must derive from the normalized durable previews, so individual preview and contact-sheet orientation agree.
6. Identity/cardinality behavior remains fail-closed and must not silently choose among conflicting UUID/orientation records.
7. Unsupported/unknown orientation values must fail closed; do not guess rotations or flips.
8. Existing `AB` previews must remain byte-identical to the raw extracted JPEG when no orientation transform is needed.
9. Package validation/order/immutability rules remain intact.

## Acceptance evidence

Automated:
- focused tests prove orientation mapping/cardinality and pixel normalization for `AB`/`BC`/`CD`/`DA`;
- unsupported/mirrored orientation fails closed;
- `AB` extraction preserves raw preview bytes while rotated outputs are valid upright JPEG artifacts;
- manifest round-trip preserves both normalized `preview_sha256` and raw `source_preview_sha256`;
- render-barrier tests prove raw-fingerprint comparison and backward compatibility for historical manifests;
- contact-sheet/session tests prove normalized previews feed the ordered package without weakening integrity checks;
- full pytest and compile/diff checks pass.

Representative live/read-only:
- query the current `ToTo Previews.lrdata` read-only and reconcile orientation values for known sideways examples (including PTO_8920/PTO_8922/PTO_8930/PTO_8931/PTO_8949) versus upright examples;
- prepare a new package/pass through the normal Lightroom command after implementation (Owner-operated if Lightroom interaction is needed);
- visual verification shows all 34 representative previews/contact-sheet tiles in the new package have intended orientation and package validation remains green.

## Stop conditions

Stop for Controller/Owner review if Lightroom cache orientation semantics are ambiguous, cache schema lacks sufficient orientation evidence, a fix would require Catalog/original mutation, or a broader architecture change is needed.

## Executed evidence so far

- Real read-only cache query: 34/34 identities resolved; 26 `AB`, 8 `DA`; known sideways frames are in the `DA` set.
- TDD orientation mapping/normalization, raw-fingerprint, historical fallback and contact-sheet orientation tests pass.
- Full pytest, integration suite, config smoke, compileall and `git diff --check` pass locally.
- Read-only real-cache scratch extraction: 34 FOUND, 0 missing/ambiguous/failed; all raw fingerprints match the immutable pre-fix package and exactly 8 normalized artifact hashes change.
- Canonical `prepare_session_pass()` against the real selection/cache in isolated runtime: 34/34 FOUND, 26 `AB` at 320×213, 8 `DA` at 213×320, 34 raw fingerprints recorded and 3 contact sheets validated.
- No Catalog, `.lrdata`, RAW, JPEG original or XMP mutation was performed.

## Live acceptance — PASS

The Owner ran the normal Lightroom `Prepare AI Package` command after the WO-040 implementation. Lightroom/Python created fresh session `sess-1788485733`, Pass 1 `pass-0001-20260904T013537Z`.

Executed package evidence:
- `pass-state.json`: 34 selected, 34 found, 3 contact sheets, package integrity artifacts present;
- durable preview dimensions: 26 landscape `(320, 213)` and 8 portrait `(213, 320)`;
- portrait outputs are exactly `PTO_8924`, `PTO_8920`, `PTO_8925`, `PTO_8922`, `PTO_8930`, `PTO_8931`, `PTO_8935`, and `PTO_8949`;
- all 34 manifest entries carry `source_preview_sha256` raw-render fingerprints;
- the three contact sheets uploaded by the Owner match the fresh runtime contact-sheet artifacts byte-for-byte by SHA-256;
- Controller visual inspection of those three sheets confirms 34/34 images display in intended orientation with no remaining sideways tile.

No Catalog Develop value, Catalog database, `.lrdata`, RAW/JPEG original, XMP, or external AI service was mutated by this verification.

## Completion state

WO-040 is complete and `LIVE_VERIFIED`. The visual package evidence is suitable to proceed to a separately selected AI-exposure judgment/calibration task. The pre-fix `sess-1788482026` package remains immutable historical defect evidence and is not rewritten in place.
