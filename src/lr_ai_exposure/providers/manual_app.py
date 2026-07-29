"""External-file provider for decisions produced by any vision-capable AI app.

A prepared job owns its decision directory. Exactly one JSON response is
resolved per FOUND manifest entry before processing begins. Missing, unknown,
duplicate, malformed, or identity-mismatched responses reject the whole batch.
The provider validates preview identity and imports decisions only; it never
writes XMP.
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
    """Resolve exactly one contained JSON response per FOUND manifest entry."""
    response_dir = Path(response_dir)
    if not response_dir.is_dir():
        raise SinglePassError(
            f"manual_response_directory is not a directory: {response_dir}"
        )
    resolved_root = response_dir.resolve()

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

    response_map: dict[str, Path] = {}
    for response_file in sorted(response_dir.glob("*.json")):
        try:
            response_file.resolve().relative_to(resolved_root)
        except ValueError:
            raise SinglePassError(
                "Response path escapes authorized response directory: "
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
                "every response must declare its image_id; rejecting."
            )

        image_id = str(declared_id)
        if image_id in response_map:
            raise SinglePassError(
                f"Duplicate response files for image_id {image_id!r}: "
                f"{response_map[image_id]} and {response_file}"
            )
        response_map[image_id] = response_file

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
    model_name: str = "external-file-agent",
) -> tuple[SinglePassDecision, dict[str, Any]]:
    """Import one external decision after preview and identity verification."""
    if not preview_full_path.exists():
        raise SinglePassError(
            f"Preview not found for {entry.image_id}: {preview_full_path}"
        )

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

    if not response_file.exists():
        raise SinglePassError(f"Manual response file not found: {response_file}")

    try:
        raw_dict = json.loads(response_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SinglePassError(
            f"Failed to parse manual response file {response_file}: {exc}"
        ) from exc

    declared_id = raw_dict.get("image_id")
    expected_id = str(entry.image_id)
    if declared_id is None:
        raise SinglePassError(
            f"Missing image_id in manual response {response_file}: rejecting."
        )
    if str(declared_id) != expected_id:
        raise SinglePassError(
            "image_id mismatch in response file: "
            f"file={declared_id!r} manifest={expected_id!r}."
        )

    decision = validate_single_pass_decision(raw_dict)
    metadata: dict[str, Any] = {
        "provider": "manual_app",
        "model": model_name,
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
            "EXTERNAL_DECISION_SCHEMA_VALID",
            "NO_XMP_MUTATION",
        ],
    }
    return decision, metadata
