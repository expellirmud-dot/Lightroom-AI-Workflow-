"""Job directory and ordered manifest foundation for lr_ai_exposure.

This module implements the bounded WO-005 capability: unique job folders
beneath ``runtime/jobs/`` and a strict, ordered ``manifest.json``.

Safety boundaries (non-negotiable):
- Job directories are created only beneath the configured runtime jobs root.
- No real photographs, XMP files, or catalog data are touched here.
- Manifest paths are validated against path-escape outside the job directory.
- Duplicate ``seq`` values, duplicate ``image_id`` values, malformed paths,
  and missing required fields are rejected.
- All I/O uses ``pathlib`` for Windows-safe paths.
- This module does NOT implement Lightroom SDK, AI, preview export, or
  XMP mutation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class ManifestError(ValueError):
    """Raised when a manifest or job directory is invalid."""


# Required fields for each manifest entry, with expected types.
_REQUIRED_ENTRY_FIELDS = {
    "image_id": str,
    "raw_path": str,
    "source_xmp_path": str,
    "backup_relative_path": str,
    "preview_path": str,
    "seq": int,
    "extraction_status": str,
}

# Subdirectories created inside every job directory.
_JOB_SUBDIRS = ("previews", "xmp_backups", "results", "logs")

@dataclass(frozen=True)
class ManifestEntry:
    """One strictly-ordered entry in a job manifest.

    ``seq`` preserves Lightroom selection order as an explicit integer.
    All path fields are stored as strings and resolved against the job
    directory at validation time.
    """

    image_id: str
    raw_path: str
    source_xmp_path: str
    backup_relative_path: str
    preview_path: str
    seq: int
    extraction_status: str = "PENDING"
    uuid: Optional[str] = None
    preview_bytes: int = 0
    preview_sha256: Optional[str] = None


@dataclass(frozen=True)
class Manifest:
    """Ordered container for manifest entries.

    ``entries`` preserves manifest order. ``job_id`` identifies the job
    directory. Validation enforces uniqueness and path safety.
    """

    job_id: str
    pass_number: int = 1
    pass_id: str = ""
    parent_pass_id: Optional[str] = None
    entries: list[ManifestEntry] = field(default_factory=list)
    total_selected: int = 0
    total_found: int = 0
    total_missing: int = 0
    total_ambiguous: int = 0
    total_failed: int = 0


def create_job_directory(runtime_root: Path, job_id: Optional[str] = None) -> Path:
    """Create a unique job directory beneath ``runtime_root/jobs``.

    If ``job_id`` is omitted, a timestamp-based unique id is generated.
    Raises ``ManifestError`` if the resolved path is not safely beneath
    ``runtime_root/jobs``.

    Returns the created job directory path.
    """
    jobs_root = Path(runtime_root) / "jobs"
    if job_id is None or job_id.strip() == "":
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        job_id = f"job-{stamp}"
    else:
        job_id = _sanitize_job_id(job_id)

    jobs_root.mkdir(parents=True, exist_ok=True)
    job_dir = jobs_root / job_id

    # Path-escape guard: resolved job_dir must stay within jobs_root.
    job_dir.resolve().relative_to(jobs_root.resolve())

    if job_dir.exists():
        # Timestamp ids are unique; an explicit colliding id is rejected.
        if job_id.startswith("job-"):
            raise ManifestError(f"Job directory already exists: {job_dir}")
        raise ManifestError(f"Job id collision: {job_id}")

    job_dir.mkdir(parents=True, exist_ok=False)
    for sub in _JOB_SUBDIRS:
        (job_dir / sub).mkdir(parents=True, exist_ok=True)

    return job_dir


def _sanitize_job_id(job_id: str) -> str:
    """Reject job ids that could escape or confuse the directory layout."""
    if not job_id or job_id in (".", ".."):
        raise ManifestError(f"Invalid job id: {job_id!r}")
    if "/" in job_id or "\\" in job_id or job_id.startswith(".."):
        raise ManifestError(f"Job id must not contain path separators: {job_id!r}")
    return job_id


def validate_manifest_entries(
    entries: list[ManifestEntry], job_dir: Path
) -> None:
    """Validate manifest entries for duplicates, order, and path safety.

    Raises ``ManifestError`` on:
    - duplicate ``seq`` values
    - duplicate ``image_id`` values
    - non-positive or out-of-range ``seq``
    - empty or malformed required fields
    - path escape outside ``job_dir``
    """
    if not entries:
        raise ManifestError("Manifest must contain at least one entry")

    seen_seq: set[int] = set()
    seen_ids: set[str] = set()
    seen_previews: set[str] = set()
    seen_raws: set[str] = set()
    expected_seq = 1

    for idx, entry in enumerate(entries):
        # Required fields present and typed
        for field_name, expected_type in _REQUIRED_ENTRY_FIELDS.items():
            value = getattr(entry, field_name)
            if not isinstance(value, expected_type):
                raise ManifestError(
                    f"Entry {idx}: field {field_name!r} must be "
                    f"{expected_type.__name__}, got {type(value).__name__}"
                )
            if isinstance(value, str) and not value.strip():
                raise ManifestError(
                    f"Entry {idx}: field {field_name!r} must not be empty"
                )

        # Duplicate seq
        if entry.seq in seen_seq:
            raise ManifestError(f"Duplicate seq value: {entry.seq}")
        seen_seq.add(entry.seq)

        # Duplicate image_id
        if entry.image_id in seen_ids:
            raise ManifestError(f"Duplicate image_id: {entry.image_id}")
        seen_ids.add(entry.image_id)

        # Duplicate preview_path
        if entry.preview_path in seen_previews:
            raise ManifestError(f"Duplicate preview_path: {entry.preview_path}")
        seen_previews.add(entry.preview_path)

        # Duplicate raw_path
        if entry.raw_path in seen_raws:
            raise ManifestError(f"Duplicate raw_path: {entry.raw_path}")
        seen_raws.add(entry.raw_path)

        # seq must be a positive integer and contiguous from 1
        if entry.seq < 1:
            raise ManifestError(f"Entry {idx}: seq must be >= 1, got {entry.seq}")
        if entry.seq != expected_seq:
            raise ManifestError(
                f"Entry {idx}: seq must be contiguous from 1, "
                f"expected {expected_seq}, got {entry.seq}"
            )
        expected_seq += 1

        # Path-escape guard for every path field that lives in job_dir
        _assert_path_inside(job_dir, entry.backup_relative_path, f"entry {idx} backup_relative_path")
        _assert_path_inside(job_dir, entry.preview_path, f"entry {idx} preview_path")


def _assert_path_inside(job_dir: Path, path_str: str, label: str) -> None:
    """Raise ManifestError if ``path_str`` escapes ``job_dir``."""
    if not path_str:
        raise ManifestError(f"{label} must not be empty")
    candidate = (job_dir / path_str).resolve()
    job_resolved = job_dir.resolve()
    try:
        candidate.relative_to(job_resolved)
    except ValueError:
        raise ManifestError(
            f"{label} escapes job directory: {path_str!r}"
        ) from None


def write_manifest(job_dir: Path, manifest: Manifest) -> Path:
    """Write ``manifest.json`` deterministically as UTF-8.

    Entries are written in manifest order. Returns the manifest path.
    """
    job_dir = Path(job_dir)
    validate_manifest_entries(manifest.entries, job_dir)

    payload = {
        "job_id": manifest.job_id,
        "pass_number": manifest.pass_number,
        "pass_id": manifest.pass_id,
        "parent_pass_id": manifest.parent_pass_id,
        "total_selected": manifest.total_selected,
        "total_found": manifest.total_found,
        "total_missing": manifest.total_missing,
        "total_ambiguous": manifest.total_ambiguous,
        "total_failed": manifest.total_failed,
        "entries": [
            {
                "image_id": e.image_id,
                "raw_path": e.raw_path,
                "source_xmp_path": e.source_xmp_path,
                "backup_relative_path": e.backup_relative_path,
                "preview_path": e.preview_path,
                "seq": e.seq,
                "extraction_status": e.extraction_status,
                "uuid": e.uuid,
                "preview_bytes": e.preview_bytes,
                "preview_sha256": e.preview_sha256,
            }
            for e in manifest.entries
        ],
    }

    manifest_path = job_dir / "manifest.json"
    temp_manifest_path = job_dir / "manifest.json.tmp"
    temp_manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temp_manifest_path.replace(manifest_path)
    return manifest_path


def read_manifest(job_dir: Path) -> Manifest:
    """Read and validate ``manifest.json`` from ``job_dir``.

    Raises ``ManifestError`` if the file is missing, malformed, or fails
    validation.
    """
    job_dir = Path(job_dir)
    manifest_path = job_dir / "manifest.json"
    if not manifest_path.exists():
        raise ManifestError(f"Manifest not found: {manifest_path}")

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Malformed manifest JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ManifestError("Manifest root must be a JSON object")
    if "entries" not in raw or not isinstance(raw["entries"], list):
        raise ManifestError("Manifest must contain an 'entries' array")

    entries: list[ManifestEntry] = []
    for idx, item in enumerate(raw["entries"]):
        if not isinstance(item, dict):
            raise ManifestError(f"Entry {idx} must be a JSON object")
        missing = [
            f for f in _REQUIRED_ENTRY_FIELDS if f not in item
        ]
        if missing:
            raise ManifestError(
                f"Entry {idx} missing required fields: {missing}"
            )
        try:
            entries.append(
                ManifestEntry(
                    image_id=item["image_id"],
                    raw_path=item["raw_path"],
                    source_xmp_path=item["source_xmp_path"],
                    backup_relative_path=item["backup_relative_path"],
                    preview_path=item["preview_path"],
                    seq=int(item["seq"]),
                    extraction_status=item.get("extraction_status", "PENDING"),
                    uuid=item.get("uuid"),
                    preview_bytes=int(item.get("preview_bytes", 0)),
                    preview_sha256=item.get("preview_sha256"),
                )
            )
        except (TypeError, ValueError) as exc:
            raise ManifestError(f"Entry {idx} has invalid field types: {exc}") from exc

    job_id = raw.get("job_id", job_dir.name)
    manifest = Manifest(
        job_id=job_id,
        pass_number=raw.get("pass_number", 1),
        pass_id=raw.get("pass_id", ""),
        parent_pass_id=raw.get("parent_pass_id"),
        entries=entries,
        total_selected=raw.get("total_selected", 0),
        total_found=raw.get("total_found", 0),
        total_missing=raw.get("total_missing", 0),
        total_ambiguous=raw.get("total_ambiguous", 0),
        total_failed=raw.get("total_failed", 0),
    )
    validate_manifest_entries(manifest.entries, job_dir)
    return manifest


__all__ = [
    "ManifestError",
    "ManifestEntry",
    "Manifest",
    "create_job_directory",
    "validate_manifest_entries",
    "write_manifest",
    "read_manifest",
]
