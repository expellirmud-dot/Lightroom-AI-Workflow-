from __future__ import annotations

import logging
from typing import Mapping

from lr_ai_exposure.session import SessionState
from lr_ai_exposure.job import Manifest


def validate_render_barrier(
    state: SessionState,
    manifest: Manifest,
    catalog_exposure2012: Mapping[str, float] | None = None,
    tolerance: float = 0.01,
) -> dict[str, str]:
    """Validate freshness before allowing an adjusted image into the next pass.

    The iterative session is Catalog-authoritative. Freshness requires:
    1. The current Catalog Exposure2012 equals the session's expected value.
    2. A valid refreshed preview exists.
    3. The refreshed preview hash differs from the pre-apply preview hash.

    XMP is deliberately not consulted here. The legacy prepared-job workflow
    retains its independent sidecar safeguards.
    """
    results: dict[str, str] = {}
    catalog_values = {str(k): float(v) for k, v in (catalog_exposure2012 or {}).items()}

    for entry in manifest.entries:
        img_id = str(entry.image_id)
        if img_id not in state.images:
            continue

        img = state.images[img_id]
        if img.status != "ADJUST":
            results[img_id] = "SKIPPED_NOT_ADJUSTED"
            continue

        expected = img.expected_exposure2012
        if expected is None:
            img.status = "REVIEW"
            results[img_id] = "REVIEW_RENDER_UNPROVEN_EXPECTED_MISSING"
            continue

        if img_id not in catalog_values:
            img.status = "REVIEW"
            results[img_id] = "REVIEW_RENDER_UNPROVEN_CATALOG_EXPOSURE_MISSING"
            continue

        actual = catalog_values[img_id]
        if abs(actual - expected) > tolerance:
            img.status = "REVIEW"
            status_msg = (
                "REVIEW_RENDER_UNPROVEN_CATALOG_MISMATCH: "
                f"expected {expected}, found {actual}"
            )
            results[img_id] = status_msg
            logging.warning("Image %s: %s", img_id, status_msg)
            continue

        if not entry.preview_sha256 or entry.preview_bytes <= 0:
            img.status = "REVIEW"
            status_msg = "REVIEW_RENDER_UNPROVEN_PREVIEW_INVALID"
            results[img_id] = status_msg
            logging.warning("Image %s: %s", img_id, status_msg)
            continue

        if img.last_preview_sha256 is not None and entry.preview_sha256 == img.last_preview_sha256:
            img.status = "REVIEW"
            status_msg = "REVIEW_RENDER_UNPROVEN_HASH_UNCHANGED"
            results[img_id] = status_msg
            logging.warning("Image %s: %s", img_id, status_msg)
            continue

        results[img_id] = "FRESH"

    return results
