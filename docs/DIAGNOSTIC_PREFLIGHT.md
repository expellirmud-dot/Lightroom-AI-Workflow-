# Lightroom Folder Diagnostic Contract

`DIAGNOSE_CURRENT_FOLDER` is the first implementation seam for the approved
Exposure Session architecture. WO-031 implements the read-only plug-in, CLI,
bridge, cache probe, XMP-readiness probe, and report path. Automated evidence
is green; a real Lightroom owner run remains pending.

## Purpose

One real Lightroom run should reveal every independently discoverable problem
instead of failing one stage at a time. Diagnostics are read-only with respect
to photographs, XMP, Lightroom catalog, and live preview cache.

## Outputs

Every completed invocation writes both:

- `preflight.json` for deterministic processing;
- `diagnostic.txt` for owner review.

The plug-in dialog shows a bounded summary and the report path. Reports must be
written even when direct photo count or eligible RAW count is zero, unless the
runtime report location itself is unavailable.

## Stage model

Each stage returns `PASS`, `WARN`, `FAIL`, or `SKIPPED_DEPENDENCY` plus stable
reason codes and evidence. A failed stage does not suppress independent later
stages. Dependent work is skipped explicitly rather than attempted blindly.

## Required evidence

### Lightroom context

- plug-in version and bridge protocol version;
- active catalog path as reported by Lightroom, without opening the catalog;
- every active source's type, name, and path;
- exact active-folder cardinality and selected folder path;
- direct `getPhotos(false)` count.

### Eligibility

- observed `fileFormat` histogram including value type and nil/empty values;
- virtual-copy, video, unsupported-format, empty-path, offline/missing-file,
  and duplicate-path counts;
- eligible proprietary-RAW master count;
- bounded sample filenames, local IDs, UUIDs, paths, and relevant raw metadata
  per category;
- canonical path collision and source-folder containment findings.

### XMP and metadata synchronization readiness

- sidecar existence and one unambiguous finite Exposure2012 value;
- Lightroom metadata synchronization evidence available through the supported
  SDK/runtime seam;
- whether sync safety is proven, disproven, or unknown;
- exact evidence that would require an owner metadata-save action.

Unknown sync safety is fail closed for session/apply readiness. It must not be
translated into an unconditional instruction to Save Metadata when no evidence
shows that action is necessary.

### Preview cache

- configured preview-cache path and its relationship to the active catalog;
- `previews.db` and `root-pixels.db` existence, size, and modification evidence;
- read-only open and bounded SQLite integrity result;
- required table/column availability;
- eligible identity mapping totals: FOUND, MISSING, AMBIGUOUS, DB_ERROR;
- bounded sample extraction/JPEG validation evidence when eligible identities
  exist.

The live `.lrdata` is never written. Any database consistency work uses the
existing read-only snapshot boundary.

### Runtime, CLI, and bridge

- configured repository/runtime paths and write readiness of the authorized
  runtime diagnostic location;
- `uv` and `lr-ai-exposure` resolution/version readiness;
- configuration-check result without printing secrets;
- request/result path readiness, protocol version, exit-status/result-status
  consistency, and UTF-8 JSON round trip;
- capability readiness for later session/pass operations, reported as planned
  until implemented.

## Summary and severity

The report contains aggregate counts and a complete issue list ordered by
severity and stage. It distinguishes:

- `READY_FOR_SESSION` - every required precondition is proven;
- `NOT_READY_FIXABLE` - bounded owner/runtime action can resolve the issue;
- `NOT_READY_UNSUPPORTED` - current inputs are outside the sidecar workflow;
- `SAFETY_BLOCKED` - identity, metadata, cache, authorization, or proof is not
  safe enough to proceed.

Diagnostic success means the report completed truthfully. It does not mean the
folder is ready, and it never authorizes AI or XMP mutation.

## Implemented boundary

- The plug-in writes only its diagnostic request/result staging files and does
  not call Prepare, Apply, AI, metadata refresh, or XMP mutation paths.
- Python opens preview-cache SQLite files with `mode=ro`, performs a bounded
  `quick_check(1)`, validates required tables/columns, and reads bounded JPEG
  header/byte-count evidence without extracting files.
- XMP readiness uses the existing strict Exposure2012 parser without backup,
  temp, replace, or rollback operations.
- Metadata synchronization is reported as `UNPROVEN` until a supported
  Lightroom evidence seam exists. This fails closed for later mutation but
  does not instruct the owner to Save Metadata without evidence.
- The current automated boundary is `INTEGRATED`, not `LIVE_VERIFIED`.
