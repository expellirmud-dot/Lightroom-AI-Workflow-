# Accepted Decisions — Lightroom AI Exposure MVP

## Project Decisions

### Architecture

- **Separate project** at `D:\ai-tools\lightroom-ai-exposure`. Isolated from `ai-worker-harness` to keep scopes clean and avoid cross-contamination.
- **No direct Catalog or Preview-cache access in MVP.** Lightroom plugin provides rendered JPEG previews and manifest metadata via file handoff only.
- **Lightroom plugin renders selected previews** in a later Work Order (WO-002+). This Work Order does not implement the plugin.
- **File handoff + one-shot CLI** is the initial IPC mechanism. No Flask, FastAPI, resident HTTP server, or file watcher in MVP.
- **Only `crs:Exposure2012`** may eventually be mutated. All other Lightroom develop properties are out of scope.
- **Default execution is dry_run.** Creates plans without mutating user files.
- **Final export remains manual.** The user controls Lightroom export after reviewing results.

### Risk Decisions

- **XMP writes use backup + temp file + atomic replace.** Failed writes leave originals intact.
- **AI output is untrusted input.** Every decision is schema-validated and clamped before use.
- **No API keys in tracked files.** Secrets live in `.env` (gitignored) or environment variables only.
- **No broad staging (`git add .`).** Only explicitly allowed files are committed.
- **Workers do not commit or push.** Commit/push only by authorized Work Orders.

### Scope Decisions

| Decision | Rationale |
|----------|-----------|
| `crs:Exposure2012` only | MVP adjusts exposure only; keeps risk minimal and predictable |
| One-shot CLI | Avoids server lifecycle complexity for MVP |
| File handoff | Simplest IPC for MVP; previews are shared files |
| `dry_run: true` default | Safe default; user always sees what would happen |
| XMP backup before write | Recoverable changes; no destructive writes |
| Manual export | User curates final output; automation not needed for MVP |
