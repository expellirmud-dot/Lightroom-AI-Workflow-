from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from lr_ai_exposure.contact_sheets import ValidatedPreview, build_contact_sheets
from lr_ai_exposure.production_job import _production_task_text


def _preview(tmp_path: Path, seq: int) -> ValidatedPreview:
    preview_path = tmp_path / "previews" / f"{seq:06d}.jpg"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), (seq % 255, 80, 160)).save(preview_path, format="JPEG")
    entry = SimpleNamespace(
        seq=seq,
        image_id=str(seq),
        preview_path=f"previews/{seq:06d}.jpg",
    )
    return ValidatedPreview(entry=entry, path=preview_path, width=32, height=24)


def test_contact_sheet_index_bounds_visual_review_to_one_sheet_per_round(tmp_path: Path) -> None:
    previews = [_preview(tmp_path, seq) for seq in range(1, 34)]

    index_path = build_contact_sheets(tmp_path, previews)
    index = json.loads(index_path.read_text(encoding="utf-8"))

    assert index["review_round_size"] == 1
    assert index["review_rounds"] == [
        {"round_number": 1, "sheet_numbers": [1]},
        {"round_number": 2, "sheet_numbers": [2]},
        {"round_number": 3, "sheet_numbers": [3]},
    ]


def test_production_task_requires_one_overview_contact_sheet_per_round() -> None:
    task = _production_task_text(job_id="job-1", source_folder="C:/photos", image_count=33)

    assert "exactly one overview contact sheet per review round" in task.lower()
    assert "complete and persist that round's semantic decisions before opening the next" in task.lower()
