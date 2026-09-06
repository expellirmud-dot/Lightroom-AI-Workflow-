from __future__ import annotations

import logging
from typing import Mapping

from lr_ai_exposure.job import Manifest
from lr_ai_exposure.session import SessionState


def validate_render_barrier(
    state: SessionState,
    manifest: Manifest,
    catalog_exposure2012: Mapping[str, float] | None = None,
    tolerance: float = 0.01,
) -> dict[str, str]:
    """Validate freshness before admitting a later pass.

    The function is observational with respect to photographic session state.
    A stale or technically unproven render must never be converted into REVIEW.
    Callers decide whether to WAIT or fail closed before a pass is admitted.
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
            results[img_id] = "BLOCKED_RENDER_EXPECTED_MISSING"
            continue

        if img_id not in catalog_values:
            results[img_id] = "BLOCKED_RENDER_CATALOG_EXPOSURE_MISSING"
            continue

        actual = catalog_values[img_id]
        if abs(actual - expected) > tolerance:
            status_msg = (
                "BLOCKED_RENDER_CATALOG_MISMATCH: "
                f"expected {expected}, found {actual}"
            )
            results[img_id] = status_msg
            logging.warning("Image %s: %s", img_id, status_msg)
            continue

        if not entry.preview_sha256 or entry.preview_bytes <= 0:
            status_msg = "BLOCKED_RENDER_PREVIEW_INVALID"
            results[img_id] = status_msg
            logging.warning("Image %s: %s", img_id, status_msg)
            continue

        source_fingerprint = entry.source_preview_sha256 or entry.preview_sha256
        if img.last_preview_sha256 is not None and source_fingerprint == img.last_preview_sha256:
            status_msg = "WAITING_FOR_RERENDER_HASH_UNCHANGED"
            results[img_id] = status_msg
            logging.info("Image %s: %s", img_id, status_msg)
            continue

        results[img_id] = "FRESH"

    return results
