from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.seed_live_test_decisions import LiveTestSeedError, seed_decisions


def _prepared_pointer(tmp_path: Path, count: int = 3) -> Path:
    pass_dir = tmp_path / "runtime" / "sessions" / "sess-test" / "passes" / "0001"
    decisions_dir = pass_dir / "decisions"
    decisions_dir.mkdir(parents=True)
    manifest = {
        "job_id": "sess-test",
        "entries": [
            {
                "image_id": f"img-{i}",
                "extraction_status": "FOUND",
                "preview_path": f"previews/{i:06d}__img-{i}.jpg",
            }
            for i in range(1, count + 1)
        ],
    }
    (pass_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    pointer = tmp_path / "runtime" / "staging" / "latest-session.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text(
        json.dumps(
            {
                "session_id": "sess-test",
                "pass_number": 1,
                "pass_id": "pass-01",
                "session_dir": str(pass_dir.parent.parent),
                "pass_dir": str(pass_dir),
            }
        ),
        encoding="utf-8",
    )
    return pointer


def test_pass_all_seeds_one_valid_file_per_found_preview(tmp_path: Path) -> None:
    pointer = _prepared_pointer(tmp_path)
    result = seed_decisions(pointer, mode="pass-all")

    assert result["decision_count"] == 3
    assert result["adjusted_image_id"] is None
    pass_dir = Path(result["pass_dir"])
    for i in range(1, 4):
        payload = json.loads((pass_dir / "decisions" / f"img-{i}.json").read_text())
        assert payload["image_id"] == f"img-{i}"
        assert payload["action"] == "PASS"
        assert payload["delta_ev"] == 0.0
        assert payload["confidence"] == 0.99


def test_one_adjust_changes_only_first_found_image(tmp_path: Path) -> None:
    pointer = _prepared_pointer(tmp_path)
    result = seed_decisions(pointer, mode="one-adjust", delta_ev=0.10)

    assert result["adjusted_image_id"] == "img-1"
    pass_dir = Path(result["pass_dir"])
    first = json.loads((pass_dir / "decisions" / "img-1.json").read_text())
    second = json.loads((pass_dir / "decisions" / "img-2.json").read_text())
    assert first["action"] == "ADJUST"
    assert first["delta_ev"] == 0.10
    assert second["action"] == "PASS"
    assert second["delta_ev"] == 0.0


def test_refuses_to_overwrite_existing_raw_decisions_without_force(tmp_path: Path) -> None:
    pointer = _prepared_pointer(tmp_path)
    seed_decisions(pointer, mode="pass-all")
    with pytest.raises(LiveTestSeedError, match="refusing to overwrite"):
        seed_decisions(pointer, mode="one-adjust")


def test_refuses_frozen_or_already_applied_pass(tmp_path: Path) -> None:
    pointer = _prepared_pointer(tmp_path)
    pointer_doc = json.loads(pointer.read_text())
    pass_dir = Path(pointer_doc["pass_dir"])

    (pass_dir / "ai-decisions.json").write_text("{}", encoding="utf-8")
    with pytest.raises(LiveTestSeedError, match="frozen AI decisions"):
        seed_decisions(pointer)

    (pass_dir / "ai-decisions.json").unlink()
    (pass_dir / "catalog-apply-evidence.json").write_text("{}", encoding="utf-8")
    with pytest.raises(LiveTestSeedError, match="Catalog apply evidence"):
        seed_decisions(pointer)


def test_refuses_large_test_adjustment(tmp_path: Path) -> None:
    pointer = _prepared_pointer(tmp_path)
    with pytest.raises(LiveTestSeedError, match="no larger than 0.25 EV"):
        seed_decisions(pointer, mode="one-adjust", delta_ev=0.50)


def test_requires_found_previews(tmp_path: Path) -> None:
    pointer = _prepared_pointer(tmp_path, count=0)
    with pytest.raises(LiveTestSeedError, match="no FOUND previews"):
        seed_decisions(pointer)
