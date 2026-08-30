from __future__ import annotations

import logging
from pathlib import Path
from lr_ai_exposure.session import SessionState
from lr_ai_exposure.job import Manifest
from lr_ai_exposure.xmp import read_exposure_2012


def validate_render_barrier(
    state: SessionState,
    manifest: Manifest,
    tolerance: float = 0.01,
) -> dict[str, str]:
    """Validate render freshness for images before allowing them into the next pass.

    To prove render freshness for an image adjusted in the previous pass:
    1. Expected Exposure2012 must match the actual value read from sidecar XMP (if XMP is present on disk).
    2. Refreshed preview evidence (SHA-256 hash and byte count) must exist.
    3. Refreshed preview hash must not match the prior pass hash.

    If freshness cannot be proven, settlement becomes REVIEW.
    """
    results: dict[str, str] = {}
    for entry in manifest.entries:
        img_id = str(entry.image_id)
        if img_id not in state.images:
            continue

        img = state.images[img_id]

        # Only photos that were marked ADJUST in the previous pass require freshness barrier verification
        if img.status != "ADJUST":
            results[img_id] = "SKIPPED_NOT_ADJUSTED"
            continue

        # 1. Verify expected Exposure2012 in XMP if file exists on disk
        target_xmp_str = entry.source_xmp_path or img.source_xmp_path
        if img.expected_exposure2012 is not None and target_xmp_str:
            target_xmp = Path(target_xmp_str)
            if target_xmp.is_file():
                try:
                    actual_exposure = read_exposure_2012(target_xmp)
                    if abs(actual_exposure - img.expected_exposure2012) > tolerance:
                        img.status = "REVIEW"
                        status_msg = (
                            f"REVIEW_RENDER_UNPROVEN_XMP_MISMATCH: expected {img.expected_exposure2012}, "
                            f"found {actual_exposure}"
                        )
                        results[img_id] = status_msg
                        logging.warning(f"Image {img_id}: {status_msg}")
                        continue
                except Exception as exc:
                    img.status = "REVIEW"
                    status_msg = f"REVIEW_RENDER_UNPROVEN_XMP_ERROR: {exc}"
                    results[img_id] = status_msg
                    continue

        # 2. Refreshed preview evidence must exist and be valid
        if not entry.preview_sha256 or entry.preview_bytes <= 0:
            img.status = "REVIEW"
            status_msg = "REVIEW_RENDER_UNPROVEN_PREVIEW_INVALID"
            results[img_id] = status_msg
            logging.warning(f"Image {img_id}: {status_msg}")
            continue

        # 3. Refreshed preview hash must have changed from prior pass
        if img.last_preview_sha256 is not None and entry.preview_sha256 == img.last_preview_sha256:
            img.status = "REVIEW"
            status_msg = "REVIEW_RENDER_UNPROVEN_HASH_UNCHANGED"
            results[img_id] = status_msg
            logging.warning(f"Image {img_id}: {status_msg}")
            continue

        # Freshness proven
        img.last_preview_sha256 = entry.preview_sha256
        results[img_id] = "FRESH"

    return results
