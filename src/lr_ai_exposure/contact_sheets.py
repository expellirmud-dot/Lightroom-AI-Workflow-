"""Build and validate immutable contact-sheet artifacts for an AI pass package."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lr_ai_exposure.job import Manifest, ManifestEntry


CONTACT_SHEET_COLUMNS = 4
CONTACT_SHEET_ROWS = 4
CONTACT_SHEET_CAPACITY = CONTACT_SHEET_COLUMNS * CONTACT_SHEET_ROWS
CONTACT_SHEET_TILE_WIDTH = 320
CONTACT_SHEET_TILE_HEIGHT = 240
CONTACT_SHEET_INDEX_NAME = "contact-sheet-index.json"


class ContactSheetError(RuntimeError):
    """Raised when contact-sheet inputs or immutable artifacts are invalid."""


@dataclass(frozen=True)
class ValidatedPreview:
    entry: ManifestEntry
    path: Path
    width: int
    height: int


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _found_entries(manifest: Manifest) -> list[ManifestEntry]:
    return [entry for entry in manifest.entries if entry.extraction_status == "FOUND"]


def validate_extracted_previews(pass_dir: Path, manifest: Manifest) -> list[ValidatedPreview]:
    """Decode every FOUND JPEG and reconcile it with manifest byte/hash evidence."""
    pass_dir = Path(pass_dir)
    validated: list[ValidatedPreview] = []
    for entry in _found_entries(manifest):
        preview_path = pass_dir / entry.preview_path
        if not preview_path.is_file():
            raise ContactSheetError(f"FOUND preview is missing: {preview_path}")
        actual_bytes = preview_path.stat().st_size
        actual_sha256 = _sha256_file(preview_path)
        if actual_bytes != entry.preview_bytes or actual_sha256 != entry.preview_sha256:
            raise ContactSheetError(f"FOUND preview evidence mismatch: {preview_path}")
        try:
            with Image.open(preview_path) as image:
                if image.format != "JPEG":
                    raise ContactSheetError(f"FOUND preview is not a JPEG: {preview_path}")
                image.load()
                width, height = image.size
        except (OSError, ValueError) as exc:
            raise ContactSheetError(f"FOUND preview cannot be decoded: {preview_path}: {exc}") from exc
        if width <= 0 or height <= 0:
            raise ContactSheetError(f"FOUND preview has invalid dimensions: {preview_path}")
        validated.append(ValidatedPreview(entry, preview_path, width, height))
    return validated


def _atomic_write_json(path: Path, payload: object) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


def build_contact_sheets(pass_dir: Path, previews: list[ValidatedPreview]) -> Path:
    """Write ordered 4×4 JPEG sheets and their deterministic index."""
    pass_dir = Path(pass_dir)
    contact_sheets_dir = pass_dir / "contact_sheets"
    contact_sheets_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    sheet_records: list[dict[str, object]] = []

    for start in range(0, len(previews), CONTACT_SHEET_CAPACITY):
        chunk = previews[start : start + CONTACT_SHEET_CAPACITY]
        sheet_number = (start // CONTACT_SHEET_CAPACITY) + 1
        canvas = Image.new(
            "RGB",
            (CONTACT_SHEET_COLUMNS * CONTACT_SHEET_TILE_WIDTH, CONTACT_SHEET_ROWS * CONTACT_SHEET_TILE_HEIGHT),
            "white",
        )
        draw = ImageDraw.Draw(canvas)
        for offset, preview in enumerate(chunk):
            column = offset % CONTACT_SHEET_COLUMNS
            row = offset // CONTACT_SHEET_COLUMNS
            x = column * CONTACT_SHEET_TILE_WIDTH
            y = row * CONTACT_SHEET_TILE_HEIGHT
            with Image.open(preview.path) as image:
                image.load()
                image.thumbnail((CONTACT_SHEET_TILE_WIDTH, CONTACT_SHEET_TILE_HEIGHT - 24))
                image_x = x + (CONTACT_SHEET_TILE_WIDTH - image.width) // 2
                image_y = y
                canvas.paste(image.convert("RGB"), (image_x, image_y))
            filename = Path(preview.entry.preview_path).name
            short_filename = filename if len(filename) <= 34 else f"{filename[:31]}..."
            label = f"{preview.entry.seq:06d} {short_filename}"
            draw.text((x + 4, y + CONTACT_SHEET_TILE_HEIGHT - 20), label, fill="black", font=font)

        relative_sheet_path = f"contact_sheets/contact-sheet-{sheet_number:04d}.jpg"
        sheet_path = pass_dir / relative_sheet_path
        temp_path = sheet_path.with_suffix(".jpg.tmp")
        canvas.save(temp_path, format="JPEG", quality=85, optimize=False)
        os.replace(temp_path, sheet_path)
        sheet_records.append(
            {
                "sheet_number": sheet_number,
                "sheet_path": relative_sheet_path,
                "image_ids": [str(item.entry.image_id) for item in chunk],
                "preview_paths": [item.entry.preview_path for item in chunk],
                "bytes": sheet_path.stat().st_size,
                "sha256": _sha256_file(sheet_path),
            }
        )

    index_path = pass_dir / CONTACT_SHEET_INDEX_NAME
    _atomic_write_json(
        index_path,
        {
            "version": 1,
            "columns": CONTACT_SHEET_COLUMNS,
            "rows": CONTACT_SHEET_ROWS,
            "capacity": CONTACT_SHEET_CAPACITY,
            "sheets": sheet_records,
        },
    )
    return index_path


def validate_contact_sheet_package(pass_dir: Path, manifest: Manifest) -> dict[str, object]:
    """Prove index/sheet coverage, order, file evidence, and decodability."""
    pass_dir = Path(pass_dir)
    index_path = pass_dir / CONTACT_SHEET_INDEX_NAME
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContactSheetError(f"Contact-sheet index is unreadable: {index_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContactSheetError("Contact-sheet index must be an object")
    if (payload.get("columns"), payload.get("rows"), payload.get("capacity")) != (
        CONTACT_SHEET_COLUMNS,
        CONTACT_SHEET_ROWS,
        CONTACT_SHEET_CAPACITY,
    ):
        raise ContactSheetError("Contact-sheet index grid metadata is invalid")
    sheets = payload.get("sheets")
    if not isinstance(sheets, list):
        raise ContactSheetError("Contact-sheet index sheets must be a list")

    found = _found_entries(manifest)
    expected_ids = [str(entry.image_id) for entry in found]
    expected_paths = [entry.preview_path for entry in found]
    actual_ids: list[str] = []
    actual_paths: list[str] = []
    for expected_number, sheet in enumerate(sheets, 1):
        if not isinstance(sheet, dict) or sheet.get("sheet_number") != expected_number:
            raise ContactSheetError("Contact-sheet numbering is invalid")
        image_ids = sheet.get("image_ids")
        preview_paths = sheet.get("preview_paths")
        sheet_relative = sheet.get("sheet_path")
        if (
            not isinstance(image_ids, list)
            or not isinstance(preview_paths, list)
            or not isinstance(sheet_relative, str)
            or len(image_ids) != len(preview_paths)
            or not 1 <= len(image_ids) <= CONTACT_SHEET_CAPACITY
        ):
            raise ContactSheetError("Contact-sheet index mapping is invalid")
        sheet_path = pass_dir / sheet_relative
        if not sheet_path.is_file():
            raise ContactSheetError(f"Contact sheet is missing: {sheet_path}")
        if sheet.get("bytes") != sheet_path.stat().st_size or sheet.get("sha256") != _sha256_file(sheet_path):
            raise ContactSheetError(f"Contact-sheet evidence mismatch: {sheet_path}")
        try:
            with Image.open(sheet_path) as image:
                if image.format != "JPEG":
                    raise ContactSheetError(f"Contact sheet is not JPEG: {sheet_path}")
                image.load()
                if image.size != (
                    CONTACT_SHEET_COLUMNS * CONTACT_SHEET_TILE_WIDTH,
                    CONTACT_SHEET_ROWS * CONTACT_SHEET_TILE_HEIGHT,
                ):
                    raise ContactSheetError(f"Contact-sheet dimensions are invalid: {sheet_path}")
        except (OSError, ValueError) as exc:
            raise ContactSheetError(f"Contact sheet cannot be decoded: {sheet_path}: {exc}") from exc
        actual_ids.extend(str(item) for item in image_ids)
        actual_paths.extend(preview_paths)
    if actual_ids != expected_ids or actual_paths != expected_paths:
        raise ContactSheetError("Contact-sheet index does not exactly match FOUND manifest previews")
    expected_sheet_count = (len(found) + CONTACT_SHEET_CAPACITY - 1) // CONTACT_SHEET_CAPACITY
    if len(sheets) != expected_sheet_count:
        raise ContactSheetError("Contact-sheet count is invalid")
    return payload


__all__ = [
    "CONTACT_SHEET_INDEX_NAME",
    "ContactSheetError",
    "ValidatedPreview",
    "build_contact_sheets",
    "validate_contact_sheet_package",
    "validate_extracted_previews",
]
