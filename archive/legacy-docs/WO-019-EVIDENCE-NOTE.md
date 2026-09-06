# WO-019 Evidence Note: Guarded XMP Exposure Apply Pilot

## Objective
Apply approved AI exposure deltas to copied test-photo XMP sidecars with full backup, validation, and rollback. Ensure strict limits on what is modified.

## Process and Evidence

1. **Apply Logic Implementation (`src/lr_ai_exposure/apply.py`):**
   - Implemented `apply_exposure_deltas` which consumes `SinglePassDecision` and `selection.json`.
   - Correctly maps the `image_id` to the original XMP via the selection context.
   - Enforces the rule: only acts on decisions where both `relevance_verdict` and `quality_verdict` are `KEEP`.

2. **XMP Mutation and Backup Safety (`src/lr_ai_exposure/xmp.py`):**
   - Reads the existing `crs:Exposure2012`.
   - Computes the new absolute exposure (`old_exposure + delta_ev`).
   - Re-uses `write_exposure_2012` which:
     - Creates a `*.bak` byte-for-byte backup in the job's `xmp_backups/` directory.
     - Surgically replaces `crs:Exposure2012` using a regex pattern on bytes, ensuring no XML parsing side effects alter formatting, encoding, namespaces, or other metadata fields.
     - Writes to a `.tmp` file and replaces the target atomically.

3. **Dry Run vs Real Mode:**
   - Validated both dry-run (creates `.dry_run` backup, skips overwrite) and real execution.

4. **Live Validation Script (`scratch/test_wo_019.py`):**
   - Simulated an end-to-end apply process for a single dummy copied image.
   - Verified the backup file byte-for-byte equivalence.
   - Asserted that `crs:Exposure2012` changed accurately while preserving `crs:Contrast="10"`.

## Validation Results
- Pytest `tests/test_apply.py` passes.
- Scratch execution simulated successful `DRY RUN` and `SUCCESS` apply steps.
- All non-KEEP images are correctly skipped and recorded in the returned report.

## Conclusion
WO-019 is complete. Approved exposure adjustments can be safely written to XMP files using surgical replacement with guaranteed atomic backups.
