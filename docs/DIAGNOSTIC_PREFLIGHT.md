# Lightroom Folder Diagnostic Contract

## Status boundary

`DIAGNOSE_CURRENT_FOLDER` was implemented in WO-031 before the canonical
WO-034+ mutation route moved from XMP synchronization to Lightroom Catalog
`Exposure2012`.

The diagnostic remains useful read-only evidence for folder enumeration,
identity, preview-cache, runtime, CLI and bridge readiness. Its legacy
`xmp_readiness` / `metadata_sync` observations must **not** be interpreted as
canonical Catalog-session prerequisites.

WO-041 reconciles the implementation with the current Catalog-authoritative
architecture. `metadata_sync` is explicitly `NOT_REQUIRED_CATALOG_AUTHORITATIVE`;
legacy XMP readiness is advisory only; canonical preview readiness follows the
WO-042 Standard Preview tier boundary instead of RootPixels availability.

## Purpose

One read-only Lightroom run should reveal independently discoverable folder,
identity, cache and runtime problems without mutating photographs, Catalog,
sidecars or live preview cache.

## Outputs

Every completed invocation writes:

- `preflight.json` for deterministic evidence;
- `diagnostic.txt` for owner review.

Diagnostic completion means the report was produced truthfully; it does not
authorize AI or mutation.

## Stage model

Each stage returns `PASS`, `WARN`, `FAIL` or `SKIPPED_DEPENDENCY` plus stable
reason codes/evidence. Independent stages should continue after another stage
fails so the owner receives a complete bounded report.

## Canonical Catalog-session readiness evidence

### Lightroom context

- plug-in/bridge protocol identity;
- active catalog path as reported by Lightroom, without opening the database;
- active source type/name/path;
- exact source-folder scope and recursive/direct counts as applicable;
- stable Lightroom local IDs/UUIDs/source paths.

### Eligibility

- observed file-format histogram and value types;
- virtual-copy/video/unsupported/empty/offline/duplicate counts;
- eligible proprietary-RAW master count;
- bounded identity samples;
- source containment/canonical path conflicts.

### Preview cache

- configured cache path and relationship to the active catalog;
- required DB existence/read-only accessibility/schema;
- bounded SQLite integrity result;
- eligible identity mapping totals and JPEG byte/header evidence.

Since WO-042, canonical package preparation requires an existing Lightroom-rendered
preview tier at or above `preview_size` (1440 px target). The diagnostic now
checks this same boundary per eligible image: exact 1440 or the smallest existing
larger tier is ready; smaller-only/missing tiers report `PREVIEW_TIER_NOT_READY`.
`root-pixels.db` is retained only as legacy informational evidence and is not a
canonical readiness prerequisite. This condition means Lightroom needs the
relevant Standard Preview built or refreshed; Python never writes the cache or
manufactures a substitute.

The live `.lrdata` is never written.

### Runtime / CLI / bridge

- authorized runtime path/write readiness;
- `uv` / CLI/config readiness without printing secrets;
- request/result protocol and UTF-8 JSON round trip;
- result/evidence path integrity.

These stages remain relevant to the canonical package/session route.

## Catalog Exposure readiness

Canonical Prepare/Apply captures current `Exposure2012` through Lightroom SDK
Develop state. Sidecar existence is not the authority for the current iterative
baseline.

If the active Prepare/Apply command cannot capture or reconcile the required
Catalog Develop value, that command must fail closed with its own current
runtime evidence. Do not substitute an XMP value for missing Catalog truth.

## Legacy XMP / metadata observations

WO-031 also probes:

- sidecar existence / parsable `crs:Exposure2012`;
- historical metadata synchronization safety.

These remain useful only when diagnosing the preserved legacy XMP workflow.
For canonical WO-037+ sessions:

- missing/malformed XMP does not by itself make Catalog Prepare unsafe;
- `METADATA_SYNC_UNPROVEN` does not require the owner to Save Metadata;
- no XMP Save/Read ritual is required before Catalog `Exposure2012` apply;
- legacy stage failures must not be promoted into a new canonical implementation
  requirement without evidence that the active command depends on them.

## Readiness interpretation

For current planning, distinguish:

- `CANONICAL_SESSION_READY` — source identity, eligible RAWs, cache/package
  inputs and required runtime/bridge evidence are sufficient for the current
  Catalog workflow;
- `CANONICAL_SESSION_BLOCKED` — a current Catalog/package prerequisite is
  missing/unsafe;
- `LEGACY_XMP_NOT_READY` — only sidecar evidence is missing/unreadable; this is
  advisory and does not block the canonical Catalog route;
- `PREVIEW_TIER_NOT_READY` — one or more eligible images lack an existing cached
  preview tier at or above the configured target; this is a fixable current
  prerequisite, not a safety corruption condition.

The diagnostic and Prepare commands now agree on the canonical preview boundary.

## Safety

The diagnostic is read-only. It never calls Prepare/Apply/AI, never requests a
Develop mutation, never writes `.lrdata`, never opens the Catalog DB directly,
and never writes/backs up/replaces XMP.
