# Accepted Decisions — Lightroom AI Exposure Assist

## Canonical architecture

- The production workflow is **prepare once → external AI file review → apply
  the same saved job**.
- A one-shot AI/API call is not the canonical production route. Legacy CLI
  modes remain only for compatibility.
- The Lightroom plug-in snapshots and extracts all selected previews once, then
  stops.
- Any vision-capable AI app may analyze the prepared folder. The application is
  provider-agnostic and does not require a Gemini API key.
- AI decisions belong inside the prepared job at `decisions/`; a global manual
  response directory is not canonical.
- Apply reopens the exact saved job and must not read the preview cache again.
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
- Runtime jobs, previews, decisions, logs, and backups are never committed.
