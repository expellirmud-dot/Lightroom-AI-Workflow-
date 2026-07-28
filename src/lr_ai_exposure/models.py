"""Data models for lr_ai_exposure MVP scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ImageDecision:
    """One AI decision for a single image."""

    image_id: str
    delta_ev: float
    confidence: float
    reject: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ManifestEntry:
    """One entry in a job manifest."""

    image_id: str
    raw_path: str
    xmp_path: str
    preview_path: str
    sequence: int


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
