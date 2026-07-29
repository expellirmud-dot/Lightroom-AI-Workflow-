# XMP Safety Rules — Lightroom AI Exposure Assist

## Allowed property

The only Lightroom development property the program may modify is:

- `crs:Exposure2012` — exposure compensation in EV.

The calculation is:

```text
new_exposure = existing_exposure + validated_delta_ev
```

A validated delta of `0.0` must produce `SKIPPED_NO_CHANGE`; the XMP must remain
byte-identical and no backup or replace operation is needed.

## Forbidden fields

The program must never modify camera-capture EXIF, White Balance, Contrast,
Highlights, Shadows, Whites, Blacks, Clarity, Texture, Vibrance, Saturation,
Color Grade, Sharpening, Noise Reduction, Crop, Straighten, Masks, Keywords,
Rating, Label, Photoshop metadata, descriptive metadata, or timestamps owned by
Lightroom.

RAW/NEF/JPEG originals and Lightroom catalog files are immutable. Preview-cache
databases may be read only through validated snapshots and are never written.

## Saved-job identity gate

Before any XMP mutation, the application must reconcile:

- exact job ID;
- complete selection IDs against complete manifest IDs;
- decision IDs against only manifest entries whose preview status is `FOUND`;
- Lightroom `id_local` and UUID;
- exact canonical RAW path;
- exact canonical XMP path;
- prepared source-folder containment;
- decision confidence, verdicts, risk flags, and delta bounds.

A missing preview receives a terminal skip record and must not block unrelated
safe FOUND images. An identity mismatch, path mismatch, corrupted checkpoint,
unexpected mutation, or rollback failure fails closed according to batch
severity.

## Authorization

Real mutation is reachable only through the explicit Apply Prepared Job
operation and an exact `--authorize-apply <job-id>` token. The per-image
allowlist is derived from validated decisions that are KEEP/KEEP, meet the
confidence threshold, have no risk flags, and have a finite non-zero delta.

The AI never receives XMP write authority.

## Transaction procedure

Every authorized non-zero XMP write must follow this sequence:

1. Parse the existing XMP and require one unambiguous finite Exposure2012 value.
2. Read and hash the original bytes.
3. Create a byte-preserving backup inside the prepared job's `xmp_backups/`.
4. Verify the backup SHA-256 equals the original SHA-256.
5. Surgically replace only the Exposure2012 serialization in a temporary file
   beside the target.
6. Parse the temporary XMP and verify the intended value.
7. Atomically replace the original XMP.
8. Parse the target again, verify the exact expected value, and record its
   SHA-256.
9. If post-replace validation fails, restore the verified backup and prove the
   restored SHA-256.
10. If rollback fails, record `ROLLBACK_FAILED_FATAL` and halt the batch.

Apply evidence must include image ID, target XMP path, backup path, old
exposure, delta, new exposure, original hash, backup hash, final hash, status,
and error/rollback information when applicable.

## Checkpoint and resume

`apply-evidence.json` is written atomically after every image. Each selected
image receives exactly one terminal record. Reopening a saved job must not
repeat a settled image.

## Dry run and analysis

Analysis and `--process-job` never import or call the apply layer. Legacy dry
run may produce proposals but must not modify the target XMP. Prepared-job real
apply uses explicit two-key authorization rather than a persistent global
`apply_authorized` toggle.
