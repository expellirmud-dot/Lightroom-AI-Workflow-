# Canonical Folder Job Workflow

This document is the authoritative user and runtime workflow for Lightroom AI
Exposure Assist.

## Goal

Prepare every eligible master photo in the current Lightroom folder once, let
any file-capable vision AI analyze the exported job folder, save structured
decisions, and then apply only validated `crs:Exposure2012` changes to the
original XMP sidecars.

The application does not require a Gemini API call. The AI may be AGY, Gemini
CLI, Codex, another desktop app, or any other model that can read local JPEGs
and write JSON files.

## Canonical lifecycle

```text
open exactly one Lightroom folder
→ Prepare Current Folder
→ read every eligible master photo in that folder
→ read-only cache snapshot and preview extraction once
→ durable runtime/jobs/<job-id>/ bundle
→ external AI reads AI_TASK.md + previews
→ external AI writes decisions/<image_id>.json
→ Process Prepared Job (optional validation-only)
→ Apply Prepared Job (explicit authorization)
→ backup each XMP
→ update only crs:Exposure2012
→ verify or rollback each file
→ Lightroom reads metadata from successful XMP files
```

No Ctrl+A photo selection is required for preparation.

## Phase 1 — Prepare once

The Lightroom command **AI Exposure Assist — Prepare Current Folder**:

1. Reads `catalog:getActiveSources()` and requires exactly one active
   `LrFolder`.
2. Calls `folder:getPhotos(false)` to read every photo directly contained in
   that folder; child folders are not included.
3. Excludes virtual copies, videos, missing source paths, and duplicate source
   paths because they cannot own independent RAW/XMP targets in this workflow.
4. Writes `selection.json` with source folder, Lightroom `image_id`, RAW path,
   UUID, and exclusion counts.
5. Snapshots `previews.db` and `root-pixels.db` read-only.
6. Extracts one current-rendered JPEG preview per eligible master photo where
   available.
7. Writes a durable job folder.
8. Stops without calling AI and without touching XMP.

Prepared job layout:

```text
runtime/jobs/<job-id>/
├── selection.json
├── manifest.json
├── job-state.json
├── AI_TASK.md
├── decision-schema.json
├── previews/
├── decisions/
├── xmp_backups/
├── results/
└── logs/
```

A prepared job must contain photos from exactly one source folder. The plug-in
prepares the complete eligible folder in one cache handoff. If representative
runtime limits later require chunking, chunks must be derived from this one
prepared job rather than repeating Lightroom cache extraction.

## Phase 2 — External AI review

The AI reads `AI_TASK.md`, `manifest.json`, and every FOUND preview. It must use
all four project skills:

- `exposure-judgment`
- `batch-consistency-review`
- `image-relevance-triage`
- `visual-quality-safety`

The AI evaluates:

- intended subject and person priority;
- subject and background exposure;
- scene intent and atmosphere;
- highlight and shadow safety;
- focus, blur, obstruction, accidental/test-shot evidence, and usability;
- event/narrative relevance and duplicate/supporting value;
- grouping, reference-frame choice, and consistency across similar images;
- a bounded exposure delta;
- KEEP, REVIEW, or SKIP outcomes.

The AI writes exactly one JSON file for every FOUND manifest entry to:

```text
runtime/jobs/<job-id>/decisions/<image_id>.json
```

The AI never edits RAW, XMP, Lightroom catalog, preview cache, manifest, or
preview files.

## Phase 3 — Validate saved decisions

`lr-ai-exposure --process-job <job-id>` reopens the existing job. It does not
read the Lightroom cache and does not create a new job.

Validation rejects the whole analysis batch before apply when decision files
are missing, unknown, duplicated, malformed, outside the job directory, or
identity-mismatched. Validated decisions are written to `ai-decisions.json`,
`analysis-records.json`, and `analysis-evidence.json`.

## Phase 4 — Apply saved decisions

The Lightroom command **AI Exposure Assist — Apply Prepared Job** invokes:

```text
lr-ai-exposure --apply-job <job-id> --authorize-apply <job-id>
```

This explicit operation and exact job-ID token are the two authorization keys.
The application derives the per-image allowlist only from decisions that are:

- relevance `KEEP`;
- quality `KEEP`;
- at or above the configured confidence threshold;
- free of highlight/shadow risk flags;
- finite and within configured EV bounds;
- non-zero delta.

`REVIEW`, `SKIP`, low-confidence, risky, missing-preview, and zero-delta images
receive terminal skip records and are not mutated.

## XMP transaction

For every authorized image:

1. Reconcile selection, manifest, UUID, RAW path, XMP path, and decision ID.
2. Confirm the target remains inside the prepared source folder.
3. Read the existing `crs:Exposure2012` value.
4. Create a byte-preserving backup and verify SHA-256.
5. Write a validated temporary XMP.
6. Atomically replace the original XMP.
7. Verify the new value and final SHA-256.
8. Roll back from the verified backup if post-write validation fails.
9. Stop the batch immediately if rollback itself fails.

Only `crs:Exposure2012` may change. RAW files, JPEG originals, Lightroom
catalogs, and preview caches are never mutated.

## Resume and evidence

`apply-evidence.json` is checkpointed after every image. Settled images are not
processed twice. Every eligible master photo receives one terminal record,
including images whose previews could not be extracted.

The latest prepared job pointer is:

```text
runtime/staging/latest-prepared-job.json
```

Runtime jobs, previews, decisions, logs, and XMP backups are untracked runtime
artifacts and must not be committed.
