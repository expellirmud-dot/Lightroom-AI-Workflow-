# Architecture — Lightroom AI Exposure MVP

## Canonical Future Flow

```
Lightroom selection
→ Lightroom-rendered temporary JPEG previews (already include preset/develop appearance)
→ ordered manifest.json
→ one-shot Python CLI
→ Vision AI
→ validated ai-decisions.json
→ XMP backup
→ controlled Exposure2012 apply
→ result.json
→ user reads metadata into Lightroom
→ user reviews and exports manually
```

## Key Boundaries

| Boundary | Rule |
|----------|------|
| Lightroom Catalog | Never open `.lrcat`, `.lrcat-wal`, `.lrcat-shm`, or `.lrdata` in MVP |
| RAW / originals | Never modify any original photograph |
| EXIF capture fields | Never modify camera-capture metadata |
| Editable develop property | Only `crs:Exposure2012` in MVP |
| XMP writes | Backup → temp file → validate → atomic replace |
| AI output | Never trust; schema-validate, clamp, and require confidence |
| Export | Manual only in MVP |
| Delete / reject | Suggestions only in MVP; no automated deletion |
| IPC | File handoff + one-shot CLI (no HTTP server) |

## Project Layout

```
src/lr_ai_exposure/   — Python package (src layout)
    __init__.py
    config.py         — settings loader + validator
    models.py        — data models only
    main.py          — CLI entry point
config/settings.json — default configuration
docs/               — architecture, safety, and contract documents
runtime/            — jobs, logs, temp (gitignored)
tests/              — pytest suite
```

## Configuration Validation

`load_config()` reads `config/settings.json`, validates all required fields and types, resolves runtime paths relative to project root, and allows safe environment variable overrides for secret-bearing fields (without printing their values).

## Rationale for Choices

- **One-shot CLI over HTTP server**: reduces complexity for MVP; avoids session management and port conflicts.
- **File handoff over plugin direct integration**: keeps Lightroom and Python processes independent; preview files are the only shared artifact.
- **XMP sidecar modification over catalog write**: uses Lightroom's self-describing metadata format; non-destructive and reversible.
- **`dry_run: true` default**: safe default — produces plans without mutating user files.
