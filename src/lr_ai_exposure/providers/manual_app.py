"""manual_app provider — imports a manually produced JSON decision file.

This provider is used when the Google API is QUOTA_BLOCKED and a human
agent (e.g. Gemini multimodal in the current app session) produces the
structured decision directly.

The canonical decision file is: scratch/vision-response.manual.json

Provider metadata recorded:
  provider:  manual_app
  model:     Gemini 3.1 Pro High
  mode:      ANALYZE_ONLY

No XMP writes occur in this provider.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from lr_ai_exposure.job import ManifestEntry
from lr_ai_exposure.ai_judge import (
    SinglePassDecision,
    SinglePassError,
    validate_single_pass_decision,
)


def analyze_single_image_manual_app(
    entry: ManifestEntry,
    preview_full_path: Path,
    response_file: Path,
) -> tuple[SinglePassDecision, dict[str, Any]]:
    """Import and validate a manually produced SinglePassDecision JSON.

    Steps:
      1. Verify preview_full_path exists.
      2. Verify byte size matches entry.preview_bytes.
      3. Verify SHA-256 matches entry.preview_sha256.
      4. Load response_file as JSON.
      5. Assert image_id equals entry.image_id — reject mismatch.
      6. Validate through validate_single_pass_decision.
      7. Return (decision, metadata).

    Raises SinglePassError for any violation.
    No XMP writes. apply_authorized=false is enforced upstream.
    """

    # -- 1. JPEG exists -------------------------------------------------------
    if not preview_full_path.exists():
        raise SinglePassError(
            f"Preview not found for {entry.image_id}: {preview_full_path}"
        )

    # -- 2 & 3. Byte size and SHA-256 identity verification ------------------
    try:
        image_bytes = preview_full_path.read_bytes()
    except OSError as exc:
        raise SinglePassError(f"Cannot read preview bytes: {exc}") from exc

    actual_bytes = len(image_bytes)
    if actual_bytes != entry.preview_bytes:
        raise SinglePassError(
            f"Byte size mismatch: manifest={entry.preview_bytes} actual={actual_bytes}"
        )

    actual_sha256 = hashlib.sha256(image_bytes).hexdigest()
    if actual_sha256 != entry.preview_sha256:
        raise SinglePassError(
            f"SHA-256 mismatch: manifest={entry.preview_sha256} actual={actual_sha256}"
        )

    # -- 4. Load manual response file ----------------------------------------
    if not response_file.exists():
        raise SinglePassError(
            f"Manual response file not found: {response_file}"
        )

    try:
        raw_text = response_file.read_text(encoding="utf-8")
        raw_dict = json.loads(raw_text)
    except Exception as exc:
        raise SinglePassError(
            f"Failed to parse manual response file {response_file}: {exc}"
        ) from exc

    # -- 5. image_id reconciliation: reject mismatch, never silently overwrite -
    declared_id = raw_dict.get("image_id")
    expected_id = str(entry.image_id)

    if declared_id is None:
        # System-bind: insert canonical ID since model was told not to produce it
        raw_dict["image_id"] = expected_id
    elif str(declared_id) != expected_id:
        raise SinglePassError(
            f"image_id mismatch in response file: "
            f"file={declared_id!r} manifest={expected_id!r}. "
            f"Do not edit image_id after generation."
        )

    # -- 6. Schema validation -------------------------------------------------
    decision = validate_single_pass_decision(raw_dict)

    # -- 7. Metadata ----------------------------------------------------------
    metadata: dict[str, Any] = {
        "provider": "manual_app",
        "model": "Gemini 3.1 Pro High",
        "mode": "ANALYZE_ONLY",
        "response_file": str(response_file),
        "image_id": decision.image_id,
        "preview_bytes": actual_bytes,
        "preview_sha256": actual_sha256,
        "apply_authorized": False,
        "xmp_mutation": False,
        "markers": [
            "MODEL_MULTIMODAL_IMAGE_VIEW_PROVEN",
            "CANONICAL_LIGHTROOM_IDENTITY_RECONCILED",
            "MANUAL_DECISION_SCHEMA_VALID",
            "NO_XMP_MUTATION",
            "GOOGLE_API_PROVIDER_REMAINS_QUOTA_BLOCKED",
        ],
    }

    return decision, metadata
