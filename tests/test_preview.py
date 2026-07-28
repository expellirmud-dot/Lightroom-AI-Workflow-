"""Tests for WO-008 preview validation."""

from __future__ import annotations

import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from lr_ai_exposure.job import Manifest, ManifestEntry, create_job_directory
from lr_ai_exposure.preview import validate_previews


def _make_entry(
    seq: int,
    image_id: str = "PTO_1234",
    raw_path: str = "previews/PTO_1234.NEF",
    preview_path: str = "previews/PTO_1234.jpg",
) -> ManifestEntry:
    return ManifestEntry(
        image_id=image_id,
        raw_path=raw_path,
        xmp_path=f"xmp_backups/{image_id}.xmp",
        preview_path=preview_path,
        seq=seq,
    )


def test_validate_previews_success(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="success")
    
    entries = [
        _make_entry(1, "PTO_1", "previews/PTO_1.NEF", "previews/PTO_1.jpg"),
        _make_entry(2, "PTO_2", "previews/PTO_2.NEF", "previews/PTO_2.jpg"),
    ]
    manifest = Manifest("success", entries=entries)
    
    # Create valid dummy files
    for e in entries:
        (job_dir / e.preview_path).write_bytes(b"dummy")
        
    results = validate_previews(manifest, job_dir)
    assert len(results) == 2
    assert results[0].valid is True
    assert results[0].error is None
    assert results[1].valid is True


def test_validate_previews_missing_file(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="missing")
    manifest = Manifest("missing", entries=[_make_entry(1)])
    
    results = validate_previews(manifest, job_dir)
    assert len(results) == 1
    assert results[0].valid is False
    assert results[0].error is not None
    assert "missing or not a file" in results[0].error


def test_validate_previews_not_jpeg(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="not_jpeg")
    entry = _make_entry(1, preview_path="previews/PTO_1234.png")
    manifest = Manifest("not_jpeg", entries=[entry])
    (job_dir / entry.preview_path).write_bytes(b"dummy")
    
    results = validate_previews(manifest, job_dir)
    assert results[0].valid is False
    assert results[0].error is not None
    assert "must be a JPEG" in results[0].error


def test_validate_previews_stem_mismatch(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="stem")
    entry = _make_entry(1, raw_path="previews/OTHER.NEF")
    manifest = Manifest("stem", entries=[entry])
    (job_dir / entry.preview_path).write_bytes(b"dummy")
    
    results = validate_previews(manifest, job_dir)
    assert results[0].valid is False
    assert results[0].error is not None
    assert "does not match RAW stem" in results[0].error


def test_validate_previews_name_mismatch(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="name")
    entry = _make_entry(1, image_id="WRONG_ID")
    manifest = Manifest("name", entries=[entry])
    (job_dir / entry.preview_path).write_bytes(b"dummy")
    
    results = validate_previews(manifest, job_dir)
    assert results[0].valid is False
    assert results[0].error is not None
    assert "Preview name must be" in results[0].error


def test_validate_previews_path_mismatch(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="path")
    (job_dir / "wrong_folder").mkdir(exist_ok=True)
    entry = _make_entry(1, preview_path="wrong_folder/PTO_1234.jpg", raw_path="wrong_folder/PTO_1234.NEF")
    manifest = Manifest("path", entries=[entry])
    (job_dir / entry.preview_path).write_bytes(b"dummy")
    
    results = validate_previews(manifest, job_dir)
    assert results[0].valid is False
    assert results[0].error is not None
    assert "Preview path must be" in results[0].error


def test_validate_previews_duplicate_path(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="dup")
    entries = [
        _make_entry(1),
        _make_entry(2), # Identical image_id -> same path
    ]
    manifest = Manifest("dup", entries=entries)
    (job_dir / entries[0].preview_path).write_bytes(b"dummy")
    
    results = validate_previews(manifest, job_dir)
    assert results[0].valid is True
    assert results[1].valid is False
    assert results[1].error is not None
    assert "Duplicate preview path" in results[1].error


def test_validate_previews_unreadable(tmp_path: Path) -> None:
    job_dir = create_job_directory(tmp_path, job_id="unreadable")
    entry = _make_entry(1)
    manifest = Manifest("unreadable", entries=[entry])
    p = (job_dir / entry.preview_path)
    p.write_bytes(b"dummy")
    
    with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
        results = validate_previews(manifest, job_dir)
        
    assert results[0].valid is False
    assert results[0].error is not None
    assert "unreadable" in results[0].error
