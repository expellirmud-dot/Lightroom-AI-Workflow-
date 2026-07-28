# Lightroom AI Exposure Assist

A Windows-first Lightroom Classic exposure assistant.

## MVP Workflow

1. User opens a Lightroom Classic folder and selects photos.
2. Lightroom plugin renders JPEG previews with the current preset/develop appearance.
3. An ordered `manifest.json` is written listing each image, its RAW path, XMP sidecar path, and preview path.
4. A one-shot Python CLI validates the job.
5. A vision model returns one exposure decision per image.
6. Decisions are validated and clamped.
7. Existing XMP sidecars are backed up.
8. Only `crs:Exposure2012` may be changed.
9. A `result.json` report is written.
10. User reads metadata back into Lightroom and exports manually.

## Quick Start (dry_run)

```powershell
# Clone the repository
git clone https://github.com/expellirmud-dot/Lightroom-AI-Workflow-.git
cd Lightroom-AI-Workflow-

# Copy environment template
copy .env.example .env

# Validate configuration
python -m lr_ai_exposure.main --check-config

# Run tests
python -m pytest -q
```

## Project Structure

```
src/lr_ai_exposure/   — Python package (src layout)
config/settings.json  — default configuration (dry_run: true)
docs/                 — architecture, safety, and contract decisions
runtime/              — jobs, logs, temp (gitignored)
tests/                — pytest suite
```

## Non-Negotiable Boundaries (MVP)

- Do not edit RAW, NEF, JPEG originals, or Lightroom Catalog files.
- Do not read or write `.lrcat`, `.lrcat-wal`, `.lrcat-shm`, or `.lrdata` directly.
- Do not modify EXIF camera-capture fields.
- Do not modify White Balance, Contrast, Highlights, Shadows, Crop, Masks, Keywords, Rating, Label, Sharpening, or Noise Reduction.
- The only editable Lightroom development property is `crs:Exposure2012`.
- XMP backup is created before every authorized real write.
- Default execution mode is `dry_run`.

## License

See repository root for details.
