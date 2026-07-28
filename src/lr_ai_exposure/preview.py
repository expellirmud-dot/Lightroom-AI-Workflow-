"""Preview validation before AI submission.

Implements WO-008: Validates exported preview files from a manifest.
Checks existence, extension, RAW-stem mapping, and deterministic paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lr_ai_exposure.job import Manifest, ManifestEntry


@dataclass(frozen=True)
class PreviewValidationResult:
    """Structured result of preview validation for a single manifest entry."""

    entry: ManifestEntry
    valid: bool
    error: str | None = None


def validate_previews(manifest: Manifest, job_dir: Path) -> list[PreviewValidationResult]:
    """Validate all previews in a manifest.

    Checks:
    - existence and readability
    - .jpg extension
    - filename stems match raw_path stems
    - path matches expected preview_path based on image_id
    - prevents duplicate preview paths

    Returns an ordered list of PreviewValidationResult matching the manifest entries.
    """
    job_dir = Path(job_dir)
    results: list[PreviewValidationResult] = []
    seen_previews: set[Path] = set()

    for entry in manifest.entries:
        preview_rel = Path(entry.preview_path)
        raw_rel = Path(entry.raw_path)

        # Must be a JPEG file
        if preview_rel.suffix.lower() not in (".jpg", ".jpeg"):
            results.append(
                PreviewValidationResult(entry, False, "Preview must be a JPEG file")
            )
            continue

        # RAW stem mapping
        if preview_rel.stem != raw_rel.stem:
            results.append(
                PreviewValidationResult(
                    entry,
                    False,
                    f"Preview stem {preview_rel.stem!r} does not match RAW stem {raw_rel.stem!r}",
                )
            )
            continue

        # Deterministic filename expected
        expected_name = f"{entry.image_id}{preview_rel.suffix}"
        if preview_rel.name != expected_name:
            results.append(
                PreviewValidationResult(
                    entry, False, f"Preview name must be {expected_name!r}"
                )
            )
            continue

        # Path must be exactly previews/{expected_name}
        if preview_rel.parts != ("previews", expected_name):
            results.append(
                PreviewValidationResult(
                    entry, False, f"Preview path must be 'previews/{expected_name}'"
                )
            )
            continue

        abs_preview = (job_dir / preview_rel).resolve()

        if abs_preview in seen_previews:
            results.append(
                PreviewValidationResult(entry, False, "Duplicate preview path")
            )
            continue
        seen_previews.add(abs_preview)

        if not abs_preview.is_file():
            results.append(
                PreviewValidationResult(
                    entry, False, "Preview file missing or not a file"
                )
            )
            continue

        try:
            # Readability check
            with abs_preview.open("rb") as f:
                f.read(1)
        except OSError as e:
            results.append(
                PreviewValidationResult(entry, False, f"Preview file unreadable: {e}")
            )
            continue

        results.append(PreviewValidationResult(entry, True))

    return results

__all__ = ["PreviewValidationResult", "validate_previews"]
