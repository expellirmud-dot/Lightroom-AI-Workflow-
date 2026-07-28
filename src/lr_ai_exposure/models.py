"""Data models for lr_ai_exposure MVP scaffold.

Defines the strict ordered manifest-entry model and the job-level
manifest container used by the WO-005 job-directory foundation.

Field naming follows the active Work Order: ``seq`` (not ``sequence``)
preserves Lightroom selection order as an explicit integer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from lr_ai_exposure.job import (
    ManifestError,
    ManifestEntry,
    Manifest,
    create_job_directory,
    write_manifest,
    read_manifest,
    validate_manifest_entries,
)


@dataclass(frozen=True)
class ImageDecision:
    """One AI decision for a single image."""

    image_id: str
    delta_ev: float
    confidence: float
    reject: bool = False
    reason: str = ""


@dataclass(frozen=True)
class JobResult:
    """Summary result for a job."""

    total_images: int
    adjusted: int
    skipped: int
    rejected: int
    errors: int
    decisions: list[ImageDecision] = field(default_factory=list)
    xmp_backups: int = 0

    @property
    def success(self) -> bool:
        """Return True when no errors and all decisions are valid."""
        return self.errors == 0


__all__ = [
    "ImageDecision",
    "JobResult",
    "ManifestEntry",
    "Manifest",
    "ManifestError",
    "create_job_directory",
    "write_manifest",
    "read_manifest",
    "validate_manifest_entries",
]
