"""manual_app provider — imports manually produced JSON decision files.

This provider is used when the Google API is QUOTA_BLOCKED and a human
agent (e.g. Gemini multimodal in the current app session) produces the
structured decisions directly.

WO-023 batch contract: responses live in an authorized response
directory (``manual_response_directory``). Exactly one JSON response is
resolved per FOUND manifest entry via ``resolve_manual_response_map``
before any analysis begins. Missing, unknown, duplicate, malformed, or
identity-mismatched responses reject the whole batch — no partial
processing.

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


def resolve_manual_response_map(
    manifest: Any,
    response_dir: Path,
) -> dict[str, Path]:
    """Resolve exactly one JSON response per FOUND manifest entry.

    Batch preflight for the WO-023 manual provider contract. Runs
    BEFORE any analysis so that an invalid batch fails closed with no
    partial processing.

    Rejects (raises ``SinglePassError``):
      - missing / non-directory ``response_dir``
      - a response path escaping the authorized response directory
      - malformed JSON in any response file
      - a response missing ``image_id``
      - duplicate ``image_id`` across response files
      - duplicate ``image_id`` within the FOUND manifest entries
      - unknown responses (IDs not present as FOUND manifest entries)
      - missing responses (FOUND manifest IDs with no response)

    Returns a mapping ``image_id -> response_path``.
    """
    response_dir = Path(response_dir)
    if not response_dir.is_dir():
        raise SinglePassError(
            f"manual_response_directory is not a directory: {response_dir}"
        )
    resolved_root = response_dir.resolve()

    # -- collect FOUND manifest IDs, rejecting duplicates ---------------------
    found_ids: list[str] = []
    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            continue
        image_id = str(entry.image_id)
        if image_id in found_ids:
            raise SinglePassError(
                f"Duplicate image_id in manifest FOUND entries: {image_id!r}"
            )
        found_ids.append(image_id)

    # -- scan the authorized response directory -------------------------------
    response_map: dict[str, Path] = {}
    for response_file in sorted(response_dir.glob("*.json")):
        # Containment: reject any path (e.g. symlink) escaping the directory.
        try:
            response_file.resolve().relative_to(resolved_root)
        except ValueError:
            raise SinglePassError(
                f"Response path escapes authorized response directory: "
                f"{response_file}"
            )

        try:
            raw = json.loads(response_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SinglePassError(
                f"Malformed JSON in manual response {response_file}: {exc}"
            ) from exc

        declared_id = raw.get("image_id") if isinstance(raw, dict) else None
        if declared_id is None:
            raise SinglePassError(
                f"Missing image_id in manual response {response_file}: "
                f"every manual response must declare its image_id; rejecting."
            )

        image_id = str(declared_id)
        if image_id in response_map:
            raise SinglePassError(
                f"Duplicate response files for image_id {image_id!r}: "
                f"{response_map[image_id]} and {response_file}"
            )
        response_map[image_id] = response_file

    # -- exact set equality: manifest FOUND IDs == response IDs ---------------
    found_set = set(found_ids)
    response_set = set(response_map)

    unknown = sorted(response_set - found_set)
    if unknown:
        raise SinglePassError(
            f"Unknown responses with no FOUND manifest entry: {unknown}"
        )

    missing = sorted(found_set - response_set)
    if missing:
        raise SinglePassError(
            f"Missing responses for FOUND manifest entries: {missing}"
        )

    return response_map


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

    # -- 5. image_id reconciliation: reject mismatch AND missing ------------
    declared_id = raw_dict.get("image_id")
    expected_id = str(entry.image_id)

    if declared_id is None:
        # WO-023: never system-bind a missing image_id in a manual response.
        raise SinglePassError(
            f"Missing image_id in manual response {response_file}: "
            f"every manual response must declare its image_id; rejecting."
        )
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
            "JPEG_IDENTITY_VERIFIED",
            "CANONICAL_LIGHTROOM_IDENTITY_RECONCILED",
            "MANUAL_DECISION_SCHEMA_VALID",
            "NO_XMP_MUTATION",
        ],
    }

    return decision, metadata
