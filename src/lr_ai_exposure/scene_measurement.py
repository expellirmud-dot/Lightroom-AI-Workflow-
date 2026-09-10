"""Provider-neutral deterministic scene luminance measurement.

This module intentionally has no face/subject detector dependency.  It measures
an immutable rendered JPEG in display RGB so every decodable production preview
has the same numeric measurement domain.  Visual AI decides scene/reference
semantics; this module owns only deterministic pixels -> numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
import io

import numpy as np
from PIL import Image, UnidentifiedImageError


class InvalidSceneMeasurement(ValueError):
    """Raised when scene evidence cannot produce a finite positive measurement."""


@dataclass(frozen=True)
class SceneMeasurement:
    measurement: float
    highlight_clip_fraction: float
    crop_fraction: float = 0.10
    trim_fraction: float = 0.05


def measure_robust_scene_luminance(jpeg_bytes: bytes) -> SceneMeasurement:
    """Measure robust central scene luminance from a rendered JPEG.

    The outer 10% is excluded to reduce borders/edge clutter.  Within that
    central region, the darkest and brightest 5% are trimmed and the median
    Rec.709 display-domain luminance is returned.  Highlight clipping is retained
    as separate safety evidence and does not redefine the luminance target.
    """
    if not isinstance(jpeg_bytes, (bytes, bytearray)) or not jpeg_bytes:
        raise InvalidSceneMeasurement("JPEG evidence bytes are required")
    try:
        with Image.open(io.BytesIO(bytes(jpeg_bytes))) as image:
            if image.format != "JPEG":
                raise InvalidSceneMeasurement("scene evidence must be JPEG")
            rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    except InvalidSceneMeasurement:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidSceneMeasurement("scene evidence is not a decodable JPEG") from exc

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise InvalidSceneMeasurement("scene evidence RGB geometry is invalid")
    height, width = rgb.shape[:2]
    if width < 4 or height < 4:
        raise InvalidSceneMeasurement("scene evidence is too small")

    y = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    y1, y2 = int(height * 0.10), int(height * 0.90)
    x1, x2 = int(width * 0.10), int(width * 0.90)
    core = y[y1:y2, x1:x2].reshape(-1)
    if core.size == 0:
        raise InvalidSceneMeasurement("scene measurement crop is empty")
    lo, hi = np.quantile(core, [0.05, 0.95])
    trimmed = core[(core >= lo) & (core <= hi)]
    if trimmed.size == 0:
        raise InvalidSceneMeasurement("scene measurement trim is empty")
    measurement = float(np.median(trimmed))
    clip = float(np.mean(np.max(rgb, axis=2) >= (245.0 / 255.0)))
    if not np.isfinite(measurement) or measurement <= 0.0:
        raise InvalidSceneMeasurement("scene measurement must be finite and positive")
    if not np.isfinite(clip) or clip < 0.0 or clip > 1.0:
        raise InvalidSceneMeasurement("scene highlight clipping fraction is invalid")
    return SceneMeasurement(measurement=measurement, highlight_clip_fraction=clip)
