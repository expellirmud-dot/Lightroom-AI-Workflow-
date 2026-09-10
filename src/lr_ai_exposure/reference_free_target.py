"""Reference-free photographic target bracket primitives.

These helpers are deliberately non-mutating with respect to Lightroom.  They build
synthetic display-domain exposure brackets from frozen preview JPEGs so a visual
judge can select an opaque candidate ID.  Numeric Lightroom Exposure2012 remains
owned by deterministic Python calibration in ``hybrid_exposure``.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont


DEFAULT_CANDIDATE_EVS: tuple[float, ...] = (
    -2.0,
    -1.5,
    -1.0,
    -0.5,
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
)


def _srgb_to_linear(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(values: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)
    return np.where(values <= 0.0031308, values * 12.92, 1.055 * np.power(values, 1.0 / 2.4) - 0.055)


def simulate_display_exposure_jpeg(
    jpeg_bytes: bytes,
    simulated_ev: float,
    *,
    quality: int = 90,
) -> bytes:
    """Return a deterministic display-domain exposure simulation JPEG.

    This is only a visual target generator.  ``simulated_ev`` is never interpreted
    as Lightroom Exposure2012 and must not cross the Catalog mutation boundary.
    """

    if not isinstance(jpeg_bytes, (bytes, bytearray)) or not jpeg_bytes:
        raise ValueError("jpeg_bytes must be non-empty")
    ev = float(simulated_ev)
    if not math.isfinite(ev) or abs(ev) > 4.0:
        raise ValueError("simulated_ev must be finite and within +/-4")
    with Image.open(io.BytesIO(bytes(jpeg_bytes))) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    linear = _srgb_to_linear(rgb)
    exposed = np.clip(linear * (2.0**ev), 0.0, 1.0)
    srgb = _linear_to_srgb(exposed)
    out = Image.fromarray(np.rint(srgb * 255.0).astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=int(quality), optimize=False, progressive=False)
    return buf.getvalue()


def _clip_metrics(jpeg_bytes: bytes) -> tuple[float, float]:
    with Image.open(io.BytesIO(jpeg_bytes)) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    hi = float(np.mean(np.max(rgb, axis=2) >= 245))
    lo = float(np.mean(np.max(rgb, axis=2) <= 5))
    return hi, lo




def _encode_exposed_linear(linear: np.ndarray, ev: float, *, quality: int = 88) -> bytes:
    exposed = np.clip(linear * (2.0**float(ev)), 0.0, 1.0)
    srgb = _linear_to_srgb(exposed)
    out = Image.fromarray(np.rint(srgb * 255.0).astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=int(quality), optimize=False, progressive=False)
    return buf.getvalue()


def _visual_bracket_linear(jpeg_bytes: bytes, *, max_long_edge: int = 720) -> np.ndarray:
    with Image.open(io.BytesIO(jpeg_bytes)) as image:
        image = image.convert("RGB")
        if max(image.size) > max_long_edge:
            image.thumbnail((max_long_edge, max_long_edge), Image.Resampling.LANCZOS)
        rgb = np.asarray(image, dtype=np.float32) / 255.0
    return _srgb_to_linear(rgb)


def display_clip_metrics(jpeg_bytes: bytes) -> tuple[float, float]:
    """Public deterministic display clipping metrics for a frozen JPEG candidate."""
    return _clip_metrics(jpeg_bytes)

def _fit_panel(image: Image.Image, *, width: int, height: int) -> Image.Image:
    copy = image.copy().convert("RGB")
    copy.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "black")
    x = (width - copy.width) // 2
    y = (height - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def _build_sheet(
    candidates: Sequence[tuple[str, bytes]],
    *,
    panel_width: int = 360,
    panel_height: int = 270,
) -> Image.Image:
    columns = 3
    rows = math.ceil(len(candidates) / columns)
    label_height = 34
    sheet = Image.new("RGB", (columns * panel_width, rows * (panel_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (candidate_id, payload) in enumerate(candidates):
        row, column = divmod(index, columns)
        x = column * panel_width
        y = row * (panel_height + label_height)
        with Image.open(io.BytesIO(payload)) as image:
            panel = _fit_panel(image, width=panel_width, height=panel_height)
        sheet.paste(panel, (x, y))
        draw.rectangle((x, y + panel_height, x + panel_width, y + panel_height + label_height), fill="white")
        draw.text((x + 8, y + panel_height + 9), candidate_id, fill="black", font=font)
    return sheet


def build_reference_free_target_package(
    job_dir: Path | str,
    manifest: Any,
    *,
    candidate_evs: Sequence[float] = DEFAULT_CANDIDATE_EVS,
) -> dict[str, Any]:
    """Build opaque per-image visual target brackets from immutable previews."""

    directory = Path(job_dir)
    evs = tuple(float(value) for value in candidate_evs)
    if len(evs) < 3 or len(set(evs)) != len(evs) or 0.0 not in evs:
        raise ValueError("candidate_evs must be unique, contain zero, and have at least three values")
    if any(not math.isfinite(value) or abs(value) > 4.0 for value in evs):
        raise ValueError("candidate_evs must be finite and within +/-4")

    output_dir = directory / "reference-free-brackets"
    output_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for entry in manifest.entries:
        image_id = str(entry.image_id)
        preview_path = (directory / entry.preview_path).resolve()
        preview_path.relative_to(directory.resolve())
        baseline_bytes = preview_path.read_bytes()
        observed_sha = hashlib.sha256(baseline_bytes).hexdigest()
        if entry.preview_sha256 and observed_sha != entry.preview_sha256:
            raise ValueError(f"preview_sha256 mismatch for image {image_id}")
        visual_linear = _visual_bracket_linear(baseline_bytes, max_long_edge=720)
        baseline_visual = _encode_exposed_linear(visual_linear, 0.0)
        baseline_hi, baseline_lo = _clip_metrics(baseline_visual)
        rendered: list[tuple[str, bytes]] = []
        candidates: list[dict[str, Any]] = []
        for index, ev in enumerate(evs):
            candidate_id = f"c{index:02d}"
            payload = _encode_exposed_linear(visual_linear, ev)
            hi, lo = _clip_metrics(payload)
            rendered.append((candidate_id, payload))
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "simulated_display_ev": ev,
                    "is_baseline": abs(ev) <= 1e-12,
                    "highlight_clip_fraction": round(hi, 8),
                    "shadow_crush_fraction": round(lo, 8),
                    "new_highlight_clip_fraction": round(max(0.0, hi - baseline_hi), 8),
                    "new_shadow_crush_fraction": round(max(0.0, lo - baseline_lo), 8),
                }
            )
        sheet = _build_sheet(rendered)
        safe_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in image_id)
        sheet_rel = Path("reference-free-brackets") / f"{safe_id}.jpg"
        sheet.save(directory / sheet_rel, format="JPEG", quality=90, optimize=False, progressive=False)
        items.append(
            {
                "image_id": image_id,
                "baseline_preview_sha256": observed_sha,
                "sheet_path": sheet_rel.as_posix(),
                "candidate_order": [candidate["candidate_id"] for candidate in candidates],
                "candidates": candidates,
            }
        )

    result = {
        "protocol_version": "2.0",
        "result_kind": "REFERENCE_FREE_TARGET_CANDIDATES",
        "job_id": str(manifest.job_id),
        "candidate_id_authority": "OPAQUE_VISUAL_CHOICE_ONLY",
        "numeric_lightroom_exposure_authority": "NONE",
        "items": items,
    }
    path = directory / "reference-free-target-candidates.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def load_reference_free_target_candidates(job_dir: Path | str) -> dict[str, Any]:
    path = Path(job_dir) / "reference-free-target-candidates.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"reference-free target candidate manifest is unreadable: {exc}") from exc
    if not isinstance(value, dict) or value.get("result_kind") != "REFERENCE_FREE_TARGET_CANDIDATES":
        raise ValueError("reference-free target candidate manifest is invalid")
    return value


def candidate_record(
    manifest: Mapping[str, Any],
    *,
    image_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError("reference-free target candidate items are invalid")
    for item in items:
        if isinstance(item, dict) and str(item.get("image_id")) == str(image_id):
            candidates = item.get("candidates")
            if not isinstance(candidates, list):
                break
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
                    return dict(candidate)
            raise ValueError(f"unknown target candidate {candidate_id!r} for image {image_id}")
    raise ValueError(f"reference-free target image {image_id} is missing")
