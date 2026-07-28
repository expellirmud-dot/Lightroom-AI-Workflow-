"""Tests for the WO-005 job directory and ordered manifest foundation."""

from __future__ import annotations

from pathlib import Path

import pytest

from lr_ai_exposure.job import (
    ManifestError,
    ManifestEntry,
    Manifest,
    create_job_directory,
    write_manifest,
    read_manifest,
    validate_manifest_entries,
)


def _make_entry(seq: int, image_id: str = "PTO_3392") -> ManifestEntry:
    return ManifestEntry(
        image_id=image_id,
        raw_path=f"previews/{image_id}.NEF",
        xmp_path=f"xmp_backups/{image_id}.xmp",
        preview_path=f"previews/{image_id}.jpg",
        seq=seq,
    )


def test_create_job_directory_default_id(tmp_path: Path) -> None:
    """A job directory with timestamp id is created with subdirs."""
    job_dir = create_job_directory(tmp_path)
    assert job_dir.exists()
    assert job_dir.is_dir()
    for sub in ("previews", "xmp_backups", "results"):
        assert (job_dir / sub).is_dir()
    # Default id starts with job-
    assert job_dir.name.startswith("job-")


def test_create_job_directory_explicit_id(tmp_path: Path) -> None:
    """An explicit job id creates the expected directory."""
    job_dir = create_job_directory(tmp_path, job_id="wo005-demo")
    assert job_dir.name == "wo005-demo"
    assert (job_dir / "manifest.json").parent == job_dir


def test_create_job_directory_rejects_separators(tmp_path: Path) -> None:
    """Job ids with path separators are rejected."""
    with pytest.raises(ManifestError):
        create_job_directory(tmp_path, job_id="../escape")
    with pytest.raises(ManifestError):
        create_job_directory(tmp_path, job_id="a/b")


def test_create_job_directory_rejects_collision(tmp_path: Path) -> None:
    """A colliding explicit job id raises ManifestError."""
    create_job_directory(tmp_path, job_id="dup")
    with pytest.raises(ManifestError):
        create_job_directory(tmp_path, job_id="dup")


def test_write_and_read_manifest_roundtrip(tmp_path: Path) -> None:
    """A written manifest reads back identically."""
    job_dir = create_job_directory(tmp_path, job_id="roundtrip")
    entries = [
        _make_entry(1, "PTO_3392"),
        _make_entry(2, "PTO_3393"),
        _make_entry(3, "PTO_3394"),
    ]
    manifest = Manifest(job_id="roundtrip", entries=entries)
    path = write_manifest(job_dir, manifest)
    assert path == job_dir / "manifest.json"
    assert path.is_file()

    loaded = read_manifest(job_dir)
    assert loaded.job_id == "roundtrip"
    assert len(loaded.entries) == 3
    assert [e.seq for e in loaded.entries] == [1, 2, 3]
    assert loaded.entries[0].image_id == "PTO_3392"
    # Determinism: re-read yields same content
    assert path.read_text(encoding="utf-8") == (
        '{\n  "job_id": "roundtrip",\n'
        '  "total_selected": 0,\n'
        '  "total_found": 0,\n'
        '  "total_missing": 0,\n'
        '  "total_ambiguous": 0,\n'
        '  "total_failed": 0,\n'
        '  "entries": [\n'
        '    {\n'
        '      "image_id": "PTO_3392",\n'
        '      "raw_path": "previews/PTO_3392.NEF",\n'
        '      "xmp_path": "xmp_backups/PTO_3392.xmp",\n'
        '      "preview_path": "previews/PTO_3392.jpg",\n'
        '      "seq": 1,\n'
        '      "extraction_status": "PENDING",\n'
        '      "uuid": null,\n'
        '      "preview_bytes": 0,\n'
        '      "preview_sha256": null\n'
        '    },\n'
        '    {\n'
        '      "image_id": "PTO_3393",\n'
        '      "raw_path": "previews/PTO_3393.NEF",\n'
        '      "xmp_path": "xmp_backups/PTO_3393.xmp",\n'
        '      "preview_path": "previews/PTO_3393.jpg",\n'
        '      "seq": 2,\n'
        '      "extraction_status": "PENDING",\n'
        '      "uuid": null,\n'
        '      "preview_bytes": 0,\n'
        '      "preview_sha256": null\n'
        '    },\n'
        '    {\n'
        '      "image_id": "PTO_3394",\n'
        '      "raw_path": "previews/PTO_3394.NEF",\n'
        '      "xmp_path": "xmp_backups/PTO_3394.xmp",\n'
        '      "preview_path": "previews/PTO_3394.jpg",\n'
        '      "seq": 3,\n'
        '      "extraction_status": "PENDING",\n'
        '      "uuid": null,\n'
        '      "preview_bytes": 0,\n'
        '      "preview_sha256": null\n'
        '    }\n'
        '  ]\n'
        '}\n'
    )


def test_validate_manifest_rejects_empty(tmp_path: Path) -> None:
    """An empty manifest is rejected."""
    job_dir = create_job_directory(tmp_path, job_id="empty")
    with pytest.raises(ManifestError):
        validate_manifest_entries([], job_dir)


def test_validate_manifest_rejects_duplicate_seq(tmp_path: Path) -> None:
    """Duplicate seq values are rejected."""
    job_dir = create_job_directory(tmp_path, job_id="dupseq")
    entries = [_make_entry(1), _make_entry(1, "PTO_3393")]
    with pytest.raises(ManifestError, match="Duplicate seq"):
        validate_manifest_entries(entries, job_dir)


def test_validate_manifest_rejects_duplicate_image_id(tmp_path: Path) -> None:
    """Duplicate image_id values are rejected."""
    job_dir = create_job_directory(tmp_path, job_id="dupid")
    entries = [_make_entry(1), _make_entry(2, "PTO_3392")]
    with pytest.raises(ManifestError, match="Duplicate image_id"):
        validate_manifest_entries(entries, job_dir)


def test_validate_manifest_rejects_non_contiguous_seq(tmp_path: Path) -> None:
    """Non-contiguous seq values are rejected."""
    job_dir = create_job_directory(tmp_path, job_id="gap")
    entries = [_make_entry(1), _make_entry(3, "PTO_3394")]
    with pytest.raises(ManifestError, match="contiguous"):
        validate_manifest_entries(entries, job_dir)


def test_validate_manifest_rejects_zero_seq(tmp_path: Path) -> None:
    """seq must be >= 1."""
    job_dir = create_job_directory(tmp_path, job_id="zero")
    with pytest.raises(ManifestError, match="seq must be >= 1"):
        validate_manifest_entries([_make_entry(0)], job_dir)


def test_validate_manifest_rejects_empty_field(tmp_path: Path) -> None:
    """Empty required string fields are rejected."""
    job_dir = create_job_directory(tmp_path, job_id="blank")
    bad = ManifestEntry(
        image_id="",
        raw_path="previews/x.NEF",
        xmp_path="xmp_backups/x.xmp",
        preview_path="previews/x.jpg",
        seq=1,
    )
    with pytest.raises(ManifestError, match="must not be empty"):
        validate_manifest_entries([bad], job_dir)


def test_validate_manifest_rejects_path_escape(tmp_path: Path) -> None:
    """Paths escaping the job directory are rejected."""
    job_dir = create_job_directory(tmp_path, job_id="escape")
    bad = ManifestEntry(
        image_id="PTO_3392",
        raw_path="../outside/PTO_3392.NEF",
        xmp_path="xmp_backups/PTO_3392.xmp",
        preview_path="previews/PTO_3392.jpg",
        seq=1,
    )
    with pytest.raises(ManifestError, match="escapes job directory"):
        validate_manifest_entries([bad], job_dir)


def test_validate_manifest_rejects_absolute_escape(tmp_path: Path) -> None:
    """Absolute paths escaping the job directory are rejected."""
    job_dir = create_job_directory(tmp_path, job_id="absesc")
    bad = ManifestEntry(
        image_id="PTO_3392",
        raw_path="C:\\Windows\\system32\\calc.exe",
        xmp_path="xmp_backups/PTO_3392.xmp",
        preview_path="previews/PTO_3392.jpg",
        seq=1,
    )
    with pytest.raises(ManifestError, match="escapes job directory"):
        validate_manifest_entries([bad], job_dir)


def test_read_manifest_missing_file(tmp_path: Path) -> None:
    """Reading a missing manifest raises ManifestError."""
    job_dir = create_job_directory(tmp_path, job_id="missing")
    with pytest.raises(ManifestError, match="not found"):
        read_manifest(job_dir)


def test_read_manifest_malformed_json(tmp_path: Path) -> None:
    """Reading malformed manifest JSON raises ManifestError."""
    job_dir = create_job_directory(tmp_path, job_id="malformed")
    (job_dir / "manifest.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="Malformed"):
        read_manifest(job_dir)


def test_read_manifest_missing_field(tmp_path: Path) -> None:
    """A manifest entry missing a required field is rejected."""
    job_dir = create_job_directory(tmp_path, job_id="missfield")
    (job_dir / "manifest.json").write_text(
        '{\n  "job_id": "missfield",\n  "entries": [\n'
        '    {"image_id": "PTO_3392", "raw_path": "previews/PTO_3392.NEF", '
        '"xmp_path": "xmp_backups/PTO_3392.xmp", "preview_path": "previews/PTO_3392.jpg"}\n'
        "  ]\n}\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="missing required"):
        read_manifest(job_dir)
