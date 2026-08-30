"""Synthetic, non-sensitive fixtures for reproducible CLI certification (WO-024).

All fixtures are generated from deterministic, non-private data.  No
real photographs, Lightroom catalogs, .lrdata directories, RAW files,
or XMP sidecars are committed.

Fixtures live under ``tests/fixtures/`` and are consumed by
``tests/integration/`` runners.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lr_ai_exposure.job import Manifest, ManifestEntry, read_manifest

EXPECTED = 5


def _jpeg_bytes(index: int) -> bytes:
    """Deterministic, non-sensitive JPEG placeholder bytes."""
    return f"jpeg-placeholder-{index}".encode()


def _preview_sha256(index: int) -> str:
    return hashlib.sha256(_jpeg_bytes(index)).hexdigest()


def _make_entry(image_id: str, seq: int) -> ManifestEntry:
    return ManifestEntry(
        image_id=image_id,
        raw_path=f"raw/{image_id}.NEF",
        source_xmp_path=f"raw/{image_id}.xmp",
        backup_relative_path=f"xmp_backups/{image_id}.xmp",
        preview_path=f"previews/{seq:06d}__{image_id}.jpg",
        seq=seq,
        extraction_status="FOUND",
        uuid=f"uuid-{seq}",
        preview_bytes=len(_jpeg_bytes(seq)),
        preview_sha256=_preview_sha256(seq),
    )


def synthetic_manifest(job_id: str = "job-wo024") -> Manifest:
    """Five-entry synthetic manifest for certification runs."""
    entries = [_make_entry(f"img-{i}", i) for i in range(1, EXPECTED + 1)]
    return Manifest(
        job_id=job_id,
        entries=entries,
        total_selected=EXPECTED,
        total_found=EXPECTED,
        total_missing=0,
        total_ambiguous=0,
        total_failed=0,
    )


def write_synthetic_job(root: Path) -> Path:
    """Write a complete synthetic job directory under ``root``.

    Returns the job directory path.  Creates:
    - ``previews/<seq>__<image_id>.jpg`` (deterministic JPEG placeholders)
    - ``manifest.json``
    """
    job_dir = root / "jobs" / "job-wo024"
    previews = job_dir / "previews"
    previews.mkdir(parents=True, exist_ok=True)

    manifest = synthetic_manifest()
    for entry in manifest.entries:
        (job_dir / entry.preview_path).write_bytes(_jpeg_bytes(entry.seq))

    (job_dir / "manifest.json").write_text(
        json.dumps(
            {
                "job_id": manifest.job_id,
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
                "total_selected": manifest.total_selected,
                "total_found": manifest.total_found,
                "total_missing": manifest.total_missing,
                "total_ambiguous": manifest.total_ambiguous,
                "total_failed": manifest.total_failed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return job_dir


def write_selection_json(root: Path) -> Path:
    """Write a minimal ``selection.json`` (empty selection object)."""
    path = root / "selection.json"
    path.write_text("{}", encoding="utf-8")
    return path


def write_lrdata_dir(root: Path) -> Path:
    """Write a minimal ``Previews.lrdata`` directory (empty, synthetic)."""
    lrdata = root / "Previews.lrdata"
    lrdata.mkdir(exist_ok=True)
    return lrdata


def write_manual_responses(root: Path, count: int = EXPECTED) -> Path:
    """Write one valid manual response JSON per FOUND image_id.

    Returns the response directory path.
    """
    resp_dir = root / "responses"
    resp_dir.mkdir(exist_ok=True)
    for i in range(1, count + 1):
        image_id = f"img-{i}"
        (resp_dir / f"{image_id}.json").write_text(
            json.dumps(
                {
                    "image_id": image_id,
                    "action": "ADJUST", "relevance_verdict": "KEEP",
                    "quality_verdict": "KEEP",
                    "delta_ev": 0.1 * i,
                    "confidence": 0.9,
                    "highlight_risk": False,
                    "shadow_risk": False,
                    "subject_rationale": f"subject {image_id}",
                    "scene_rationale": f"scene {image_id}",
                    "scene_group_id": "group-A",
                    "reason": f"ok {image_id}",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return resp_dir


def write_negative_identity_responses(root: Path) -> Path:
    """Write responses that should be rejected by the batch preflight.

    Contains:
    - ``img-dup.json`` — duplicate of img-1 (rejected)
    - ``img-missing.json`` — declares an image_id not in manifest (rejected)
    - ``bad-json.json`` — malformed JSON (rejected)
    - ``no-id.json`` — missing image_id (rejected)
    """
    resp_dir = root / "negative-responses"
    resp_dir.mkdir(exist_ok=True)

    # Duplicate image_id (img-1 already declared by img-1.json)
    (resp_dir / "img-dup.json").write_text(
        json.dumps(
            {
                "image_id": "img-1",
                "action": "ADJUST", "relevance_verdict": "KEEP",
                "quality_verdict": "KEEP",
                "delta_ev": 0.1,
                "confidence": 0.9,
                "highlight_risk": False,
                "shadow_risk": False,
                "subject_rationale": "dup",
                "scene_rationale": "dup",
                "scene_group_id": "group-A",
                "reason": "duplicate",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Unknown image_id (not in manifest)
    (resp_dir / "img-missing.json").write_text(
        json.dumps(
            {
                "image_id": "img-99",
                "action": "ADJUST", "relevance_verdict": "KEEP",
                "quality_verdict": "KEEP",
                "delta_ev": 0.5,
                "confidence": 0.9,
                "highlight_risk": False,
                "shadow_risk": False,
                "subject_rationale": "unknown",
                "scene_rationale": "unknown",
                "scene_group_id": "group-B",
                "reason": "not in manifest",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Malformed JSON
    (resp_dir / "bad-json.json").write_text(
        "{not valid json", encoding="utf-8"
    )

    # Missing image_id
    (resp_dir / "no-id.json").write_text(
        json.dumps(
            {
                "action": "ADJUST", "relevance_verdict": "KEEP",
                "quality_verdict": "KEEP",
                "delta_ev": 0.1,
                "confidence": 0.9,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return resp_dir


def write_synthetic_xmp(root: Path) -> Path:
    """Write a minimal synthetic XMP sidecar (non-production content).

    Used only for identity-reconciliation tests; contains no
    real Lightroom-developed XMP namespace data.
    """
    xmp_path = root / "raw" / "img-1.xmp"
    xmp_path.parent.mkdir(parents=True, exist_ok=True)
    xmp_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '    <rdf:Description rdf:about="" xmlns:custom="http://example.com/custom/">\n'
        '      <custom:synthetic>true</custom:synthetic>\n'
        '    </rdf:Description>\n'
        '  </rdf:RDF>\n'
        '</x:xmpmeta>\n',
        encoding="utf-8",
    )
    return xmp_path


@pytest.fixture
def synthetic_job_dir(tmp_path: Path) -> Path:
    """Complete synthetic job directory (previews + manifest)."""
    return write_synthetic_job(tmp_path)


@pytest.fixture
def synthetic_manifest_fixture(tmp_path: Path) -> Manifest:
    """Manifest object plus job directory on disk."""
    job_dir = write_synthetic_job(tmp_path)
    return read_manifest(job_dir), job_dir


@pytest.fixture
def manual_response_dir(tmp_path: Path) -> Path:
    """Directory with one valid response per FOUND manifest entry."""
    _, job_dir = write_synthetic_job(tmp_path)
    manifest = read_manifest(job_dir)
    return write_manual_responses(tmp_path, count=len(manifest.entries))


@pytest.fixture
def negative_response_dir(tmp_path: Path) -> Path:
    """Directory with responses that should fail batch preflight."""
    _, job_dir = write_synthetic_job(tmp_path)
    return write_negative_identity_responses(tmp_path)
