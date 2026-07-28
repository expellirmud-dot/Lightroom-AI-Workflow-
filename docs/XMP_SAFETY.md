# XMP Safety Rules — Lightroom AI Exposure MVP

## Allowed Property

The only Lightroom development property that may be modified in the MVP is:

- **`crs:Exposure2012`** — exposure value in EV (electronic value)

## Forbidden Properties and Fields

The following Lightroom and EXIF properties must **never** be modified by the MVP:

| Namespace | Property | Reason |
|-----------|----------|--------|
| `exif` | `ExposureTime` | Camera capture metadata — immutable |
| `exif` | `ExposureProgram` | Camera capture metadata — immutable |
| `exif` | `ISOSpeedRatings` | Camera capture metadata — immutable |
| `exif` | `FNumber` | Camera capture metadata — immutable |
| `crs` | `WhiteBalance` | User creative choice |
| `crs` | `Contrast` | User creative choice |
| `crs` | `Highlights` | User creative choice |
| `crs` | `Shadows` | User creative choice |
| `crs` | `Whites` | User creative choice |
| `crs` | `Blacks` | User creative choice |
| `crs` | `Clarity` | User creative choice |
| `crs` | `Texture` | User creative choice |
| `crs` | `Vibrance` | User creative choice |
| `crs` | `Saturation` | User creative choice |
| `crs` | `ColorGrade` | User creative choice |
| `crs` | `Sharpening` | User creative choice |
| `crs` | `NoiseReduction` | User creative choice |
| `crs` | `Crop` | User compositional choice |
| `crs` | `Straighten` | User compositional choice |
| `crs` | `Masks` | User creative choice |
| `crs` | `Keywords` | Catalog metadata |
| `crs` | `Rating` | User curation choice |
| `crs` | `Label` | User curation choice |
| `photoshop` | All fields | Third-party metadata |
| `xmp` | `CreateDate` | Immutable timestamp |
| `xmp` | `ModifyDate` | Should be updated by Lightroom only |
| `dc` | `description`, `title`, `creator` | User metadata |

## Future Calculation

```
new_exposure = existing_exposure + validated_delta_ev
```

Where:
- `existing_exposure` is parsed from `crs:Exposure2012` in the XMP sidecar.
- `delta_ev` is the AI's numeric recommendation, clamped to `maximum_delta_ev`.
- The result is written back as a rational number in the `crs:Exposure2012` XMP attribute.

## XMP Write Procedure

Every real XMP write must follow these steps strictly:

1. **Backup** — copy the existing XMP file to `xmp-backup/` with a `.bak` suffix before any modification and compute its SHA-256.
2. **Temp write** — write the modified XMP to a temporary file in the same directory.
3. **Atomic replace** — rename the temp file over the original XMP.
4. **Validate** — confirm the target file has the expected `crs:Exposure2012` value.
5. **Rollback** — if validation fails after replace, restore the backup automatically and verify its SHA-256.
6. **If any step fails** — fail closed and record immutable evidence of the failure or rollback state.

## Dry Run

When `dry_run: true`:
- Print what *would* be changed to stdout.
- Create XMP backup to `xmp-backup/` with `.dry_run` suffix (not `.bak` — makes intent explicit).
- Do **not** touch the actual source XMP file.
