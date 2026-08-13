# Accepted Decisions — Lightroom AI Exposure Assist

## Canonical architecture

- The production workflow is **prepare current folder once → external AI file
  review → apply the same saved job**.
- A one-shot AI/API call is not the canonical production route. Legacy CLI
  modes remain only for compatibility.
- The Lightroom plug-in requires exactly one active folder and automatically
  reads every directly contained proprietary-RAW master. Manual Ctrl+A photo
  selection is not part of the canonical workflow.
- Virtual copies, videos, DNG/JPEG/TIFF/PSD and other non-RAW formats, missing
  paths, and duplicate source paths are excluded because the project is
  sidecar-only and never writes source image files.
- The plug-in snapshots and extracts the eligible folder previews once, then
  stops.
- Every prepared job is self-contained. It includes `AI_TASK.md`, strict
  schema, and `AI_SKILLS.md`, generated from the complete four canonical visual
  skill directories.
- Any vision-capable AI app may analyze the prepared folder without separate
  repository access. The application is provider-agnostic and does not require
  a Gemini API key.
- AI decisions belong inside the prepared job at `decisions/`; a global manual
  response directory is not canonical.
- Apply reopens the exact saved job, requires the matching source folder to be
  active, and must not read the preview cache or invoke AI again.
- The explicit Apply Prepared Job action plus the exact job-ID token form the
  two-key authorization boundary.

## Safety decisions

- Lightroom catalog files are never opened or modified.
- Preview-cache databases may be read only through validated SQLite snapshots;
  the live cache is never written.
- Only `crs:Exposure2012` may be modified.
- Every changed XMP uses backup, SHA-256 verification, temp write, atomic
  replace, post-write validation, and rollback.
- Zero-delta decisions never rewrite XMP.
- Non-FOUND previews receive terminal skip records rather than blocking safe
  unrelated images.
- A rollback failure halts the batch immediately.
- Runtime jobs, previews, decisions, skill bundles, logs, and backups are never
  committed.
