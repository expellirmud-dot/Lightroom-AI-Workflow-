# WO-042 — Standard Preview Cache Reuse

STATUS: COMPLETE_INTEGRATED
ACTIVATED: 2026-09-06
CLOSED: 2026-09-06

## Trigger

Owner review found that the canonical AI package still receives approximately 320-pixel root-pixel JPEGs even though Lightroom Classic is configured to maintain larger Standard Previews. Read-only inspection of the real `ToTo Previews.lrdata` proved that Lightroom already stores rendered preview tiers such as `_720`, `_960`, `_1440`, and `_1920` as JPEG files under the cache tree. The Owner explicitly requested reusing the existing 1440-class cached preview instead of creating a new render.

WO-041 remains technically INTEGRATED but is waiting for Owner Lightroom live validation. It is temporarily parked at that evidence gate so this new visual-evidence capability can be implemented first; after WO-042 (and the separately requested documentation-history cleanup) finishes, WO-041 returns as the current live-validation gate. This is not a closure or promotion of CAP-054.

## Roadmap outcome

Advance post-MVP AI judgment quality by improving the evidence presented to vision AI while preserving Lightroom as authoritative renderer and keeping `.lrdata` strictly read-only.

## Goal

For canonical AI package preparation, reuse an already-rendered Lightroom preview tier at the configured target size (1440 px long-edge target) without asking Lightroom or Python to render/downscale a new photographic preview. Prefer the exact target tier; if it does not exist, reuse the smallest existing larger tier. If no adequate cached tier exists, fail clearly rather than silently falling back to the old ~320 px root-pixel JPEG.

## Current truth

- Canonical extraction currently resolves UUID + orientation through `previews.db`, then reads `RootPixels.jpegData` from `root-pixels.db`.
- Real package `sess-1788485733` therefore contains 26 previews at `320x213` and 8 orientation-normalized previews at `213x320`.
- Real `ToTo Previews.lrdata` contains extensionless JPEG cache files named `<uuid>-<digest>_<tier>` beneath `<first-char>/<first-four-chars>/`; observed tiers include 320, 480, 720, 960, 1440, and 1920.
- A sampled `_1440` file is a real JPEG at `1440x961` and carries no EXIF Orientation; Lightroom orientation still comes from `ImageCacheEntry.orientation`.
- `ImageCacheEntry` exposes `imageId`, `uuid`, `digest`, and `orientation`, which is sufficient to locate the rendered tier deterministically.
- `config/settings.json` contains `preview_size`, but canonical package extraction does not currently use it.
- `.lrdata` is read-only by architecture and must remain so.

## Capability

Introduce `CAP-055 — Existing Lightroom Standard Preview tier reuse`.

## Authorized scope

Implementation:
- `src/lr_ai_exposure/cache_probe.py`
- `src/lr_ai_exposure/cache_extractor.py`
- `src/lr_ai_exposure/job.py`
- `src/lr_ai_exposure/handoff.py`
- `src/lr_ai_exposure/session_lifecycle.py`
- `src/lr_ai_exposure/main.py`
- `config/settings.json`

Focused tests directly covering preview-tier discovery/reuse, orientation, manifest evidence, session preparation, CLI/config propagation, and compatibility under `tests/`.

Evidence / reconciliation:
- `Work-Order/WO-042-STANDARD-PREVIEW-CACHE-REUSE.md`
- `Work-Order/CURRENT_WORK_ORDER.md`
- `docs/ROADMAP.md`
- `docs/PROJECT_STATUS.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/VALIDATION_REGISTER.md`
- `docs/DECISIONS.md`
- `docs/FOLDER_JOB_WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `docs/DIAGNOSTIC_PREFLIGHT.md` only if preview-readiness semantics materially change
- `README.md` only if user-facing configuration/behavior needs clarification

## Forbidden

- no `.lrdata` writes, deletions, renames, cache invalidation, or cache-generation commands
- no direct `.lrcat`, `.lrcat-wal`, or `.lrcat-shm` access
- no RAW/JPEG-original/XMP mutation
- no Lightroom Develop/Catalog mutation during automated or read-only validation
- no new preview rendering/export pipeline
- no downscaling/upscaling/re-encoding merely to manufacture the requested resolution
- orientation normalization may continue only for the durable package artifact when Lightroom orientation requires rotation
- no silent fallback to the old root-pixel JPEG in canonical session/package preparation
- no provider-specific AI/API coupling
- no external AI/API calls
- no destructive Git operations or force push

## Required behavior

1. Resolve one exact cache identity from the snapshotted `previews.db`: `uuid`, `digest`, and `orientation` must agree on one record.
2. Locate candidate rendered cache files only inside the expected read-only Lightroom cache bucket derived from that UUID/digest.
3. Use `preview_size` as the minimum long-edge tier target. Checked-in default becomes `1440`.
4. Selection policy is deterministic: exact target tier first; otherwise smallest available tier greater than target; never select a smaller tier.
5. If no adequate tier exists, return a distinct `PREVIEW_TIER_NOT_READY` outcome. Canonical session pass preparation must not admit an incomplete AI package by silently substituting 320 px evidence.
6. Copy the selected cached JPEG bytes into the package. For `AB`, the package JPEG remains byte-identical to the selected cached file. For supported rotated orientations (`BC`, `CD`, `DA`), reuse the selected cached render and apply only the established orientation normalization to the package artifact.
7. `source_preview_sha256` fingerprints the selected cached render before orientation normalization so render freshness follows the actual visual evidence consumed by the package.
8. Manifest evidence records the selected source tier (`source_preview_tier`) while remaining backward-compatible with historical manifests that lack it.
9. Legacy/root-pixel helper behavior may remain for compatibility tests/tools, but canonical session and prepared-package routes use the rendered cache tier path.
10. No code path writes into `Previews.lrdata`.

## Acceptance evidence

Automated / integrated:
- preview-record test proves digest is resolved together with UUID/orientation and conflicts fail closed;
- tier discovery test proves exact 1440 wins, otherwise smallest >1440 wins, and smaller-only caches return `PREVIEW_TIER_NOT_READY`;
- copy test proves `AB` package bytes are identical to source cached bytes;
- orientation test proves rotated package dimensions/orientation remain correct while the raw source fingerprint is from the selected cached tier;
- manifest round-trip preserves `source_preview_tier` and historical missing-field compatibility;
- canonical session preparation uses configured `preview_size=1440` and fails closed when an in-scope image lacks an adequate tier;
- legacy prepared-package route receives the same configured target without provider coupling;
- focused tests pass;
- full pytest passes with only documented environmental skips;
- integration suite, config smoke, compileall, and `git diff --check` pass.

Representative real-cache evidence (read-only):
- against the real `ToTo Previews.lrdata`, identify representative exact `_1440` and larger-fallback entries through `ImageCacheEntry` UUID/digest;
- copy/read at least one real 1440 cached JPEG into isolated runtime scratch and prove JPEG validity/dimensions without modifying `.lrdata`;
- exercise a representative historical selection/session in isolated runtime scratch when sufficient 1440-or-larger tiers exist and prove package previews are no longer the old 320-pixel evidence;
- no Lightroom/Catalog/original/XMP mutation.

## Stop conditions

Stop for Owner/Controller review if standard preview files cannot be mapped deterministically from current read-only cache identity, if the cache requires mutation/generation to obtain the tier, if adequate evidence would require direct Catalog DB access, or if changing freshness semantics would make prior session safety unverifiable.

## Documentation impact

- `docs/ARCHITECTURE.md`: UPDATE
- `docs/FOLDER_JOB_WORKFLOW.md`: UPDATE
- `docs/DECISIONS.md`: UPDATE
- `docs/CAPABILITY_MATRIX.md`: UPDATE
- `docs/VALIDATION_REGISTER.md`: UPDATE after execution
- `docs/PROJECT_STATUS.md`: UPDATE
- `docs/ROADMAP.md`: UPDATE
- `docs/DIAGNOSTIC_PREFLIGHT.md`: REVIEW / update only if readiness contract changes
- `README.md`: REVIEW / update if `preview_size` semantics need user-facing documentation

## Completion state

Close WO-042 when automated/integration evidence is green and representative real-cache read-only evidence proves reuse of an existing 1440-or-larger Lightroom-rendered preview without `.lrdata` mutation. CAP-055 may reach `INTEGRATED`; do not claim `LIVE_VERIFIED` unless a representative Lightroom-hosted operation is explicitly observed.

## Executed closure evidence

- focused standard-tier suite: 7/7; combined targeted regressions passed;
- full pytest: exit 0 with 2 expected environmental skips;
- integration: 6/6; config smoke reports `preview_size=1440`; compileall exit 0;
- real cache: 5,845 identities inspected read-only; exact-1440=750, larger fallback=1,714; sampled source SHA unchanged after scratch copy;
- isolated canonical real-cache package: historical 34-image selection produced 34/34 FOUND from existing 1920 tiers, 26 landscape + 8 portrait package previews, and 3 contact sheets;
- no `.lrdata`, Catalog, original, or XMP mutation.

CAP-055 is `INTEGRATED`. No Lightroom plug-in Lua file changed under WO-042, so plug-in version remains 1.2.11.
