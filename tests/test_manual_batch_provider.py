"""WO-023 manual batch provider tests.

Covers the deterministic batch contract:

- exactly one response per FOUND manifest entry (5-entry acceptance)
- exact set equality between manifest FOUND IDs and response IDs
- rejection of missing / unknown / duplicate / malformed responses
- rejection of a missing ``image_id`` (no system-binding)
- manifest-order preservation
- response containment inside the authorized response directory
- fail-closed behavior: no partial processing, no artifacts on failure

No XMP, RAW, catalog, or preview-cache file is touched; everything
lives under ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lr_ai_exposure.ai_judge import (
    SinglePassError,
    analyze_job_single_pass,
)
from lr_ai_exposure.job import Manifest, ManifestEntry
from lr_ai_exposure.providers.manual_app import resolve_manual_response_map

EXPECTED = 5


def _decision_payload(image_id: str, seq: int) -> dict:
    return {
        "image_id": image_id,
        "relevance_verdict": "KEEP",
        "quality_verdict": "KEEP",
        "delta_ev": 0.1 * seq,
        "confidence": 0.9,
        "highlight_risk": False,
        "shadow_risk": False,
        "subject_rationale": f"subject {image_id}",
        "scene_rationale": f"scene {image_id}",
        "batch_consistency_group": "group-A",
        "reason": f"ok {image_id}",
    }


def _build_job(tmp_path: Path, count: int = EXPECTED):
    """Create a synthetic job: previews on disk + matching manifest."""
    job_dir = tmp_path / "job"
    previews = job_dir / "previews"
    previews.mkdir(parents=True)

    entries = []
    for i in range(1, count + 1):
        image_id = f"img-{i}"
        content = f"jpeg-bytes-{i}".encode()
        preview_rel = f"previews/{i:06d}__{image_id}.jpg"
        (job_dir / preview_rel).write_bytes(content)
        entries.append(
            ManifestEntry(
                image_id=image_id,
                raw_path=f"raw/{image_id}.NEF",
                source_xmp_path=f"raw/{image_id}.xmp",
                backup_relative_path=f"xmp_backups/{image_id}.xmp",
                preview_path=preview_rel,
                seq=i,
                extraction_status="FOUND",
                uuid=f"uuid-{i}",
                preview_bytes=len(content),
                preview_sha256=hashlib.sha256(content).hexdigest(),
            )
        )
    manifest = Manifest(job_id="job-wo023", entries=entries)
    return job_dir, manifest


def _write_responses(tmp_path: Path, manifest: Manifest) -> Path:
    """Write one valid response file per FOUND manifest entry."""
    resp_dir = tmp_path / "responses"
    resp_dir.mkdir(exist_ok=True)
    for entry in manifest.entries:
        if entry.extraction_status != "FOUND":
            continue
        (resp_dir / f"{entry.image_id}.json").write_text(
            json.dumps(_decision_payload(entry.image_id, entry.seq)),
            encoding="utf-8",
        )
    return resp_dir


def _config(resp_dir: Path) -> dict:
    return {
        "ai_provider": "manual_app",
        "ai_model": "Gemini 3.1 Pro High",
        "manual_response_directory": str(resp_dir),
    }


# ---------------------------------------------------------------------------
# resolve_manual_response_map — batch preflight
# ---------------------------------------------------------------------------


def test_resolve_map_five_entries_exact(tmp_path):
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)

    response_map = resolve_manual_response_map(manifest, resp_dir)

    assert len(response_map) == EXPECTED
    assert set(response_map) == {f"img-{i}" for i in range(1, EXPECTED + 1)}
    for path in response_map.values():
        assert path.parent == resp_dir


def test_resolve_map_missing_response_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)
    (resp_dir / "img-3.json").unlink()

    with pytest.raises(SinglePassError, match="Missing responses.*img-3"):
        resolve_manual_response_map(manifest, resp_dir)


def test_resolve_map_unknown_response_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)
    (resp_dir / "img-99.json").write_text(
        json.dumps(_decision_payload("img-99", 9)), encoding="utf-8"
    )

    with pytest.raises(SinglePassError, match="Unknown responses.*img-99"):
        resolve_manual_response_map(manifest, resp_dir)


def test_resolve_map_duplicate_response_id_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)
    # Second file declaring an already-mapped image_id.
    (resp_dir / "zz-dup.json").write_text(
        json.dumps(_decision_payload("img-1", 1)), encoding="utf-8"
    )

    with pytest.raises(SinglePassError, match="Duplicate response files.*img-1"):
        resolve_manual_response_map(manifest, resp_dir)


def test_resolve_map_malformed_json_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)
    (resp_dir / "img-2.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(SinglePassError, match="Malformed JSON"):
        resolve_manual_response_map(manifest, resp_dir)


def test_resolve_map_missing_image_id_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)
    payload = _decision_payload("img-4", 4)
    del payload["image_id"]
    (resp_dir / "img-4.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SinglePassError, match="Missing image_id"):
        resolve_manual_response_map(manifest, resp_dir)


def test_resolve_map_duplicate_manifest_id_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path, count=2)
    dup = manifest.entries[0]
    manifest.entries.append(dup)
    resp_dir = _write_responses(tmp_path, manifest)

    with pytest.raises(SinglePassError, match="Duplicate image_id in manifest"):
        resolve_manual_response_map(manifest, resp_dir)


def test_resolve_map_nonexistent_directory_rejected(tmp_path):
    job_dir, manifest = _build_job(tmp_path, count=1)

    with pytest.raises(SinglePassError, match="not a directory"):
        resolve_manual_response_map(manifest, tmp_path / "nope")


def test_resolve_map_symlink_escape_rejected(tmp_path):
    """A response path resolving outside the authorized directory is rejected."""
    job_dir, manifest = _build_job(tmp_path, count=1)
    resp_dir = _write_responses(tmp_path, manifest)

    outside = tmp_path / "outside.json"
    outside.write_text(
        json.dumps(_decision_payload("img-1", 1)), encoding="utf-8"
    )
    link = resp_dir / "img-1.json"
    link.unlink()
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not permitted on this Windows environment")

    with pytest.raises(
        SinglePassError, match="escapes authorized response directory"
    ):
        resolve_manual_response_map(manifest, resp_dir)


# ---------------------------------------------------------------------------
# analyze_job_single_pass — end-to-end batch behavior
# ---------------------------------------------------------------------------


def test_batch_five_decisions_in_manifest_order(tmp_path):
    """Acceptance: 5-entry manifest consumes exactly 5 responses, in order."""
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)

    decisions = analyze_job_single_pass(manifest, job_dir, _config(resp_dir))

    assert len(decisions) == EXPECTED
    for idx, entry in enumerate(manifest.entries):
        assert decisions[idx].image_id == entry.image_id
        assert decisions[idx].delta_ev == pytest.approx(0.1 * entry.seq)

    # Evidence records written beside the decisions.
    records_path = job_dir / "analysis-records.json"
    assert records_path.exists()
    doc = json.loads(records_path.read_text(encoding="utf-8"))
    assert doc["job_id"] == "job-wo023"
    assert doc["record_count"] == EXPECTED
    for idx, entry in enumerate(manifest.entries):
        record = doc["records"][idx]
        assert record["decision"]["image_id"] == entry.image_id
        assert record["provider"] == "manual_app"
        assert record["mode"] == "ANALYZE_ONLY"
        assert record["preview_bytes"] == entry.preview_bytes
        assert record["preview_sha256"] == entry.preview_sha256
        assert record["response_reference"].endswith(f"{entry.image_id}.json")
        # Full decision schema preserved — no dropped risk/rationale fields.
        for field in (
            "highlight_risk",
            "shadow_risk",
            "subject_rationale",
            "scene_rationale",
            "batch_consistency_group",
            "reason",
        ):
            assert field in record["decision"]


def test_batch_missing_response_fails_before_processing(tmp_path):
    """Fail-closed: an incomplete batch produces no decisions and no records."""
    job_dir, manifest = _build_job(tmp_path)
    resp_dir = _write_responses(tmp_path, manifest)
    (resp_dir / "img-5.json").unlink()

    with pytest.raises(SinglePassError, match="Missing responses"):
        analyze_job_single_pass(manifest, job_dir, _config(resp_dir))

    assert not (job_dir / "analysis-records.json").exists()


def test_batch_requires_response_directory_config(tmp_path):
    job_dir, manifest = _build_job(tmp_path, count=1)

    with pytest.raises(
        SinglePassError, match="manual_response_directory"
    ):
        analyze_job_single_pass(
            manifest,
            job_dir,
            {"ai_provider": "manual_app", "ai_model": "m"},
        )


def test_batch_identity_mismatch_inside_response_rejected(tmp_path):
    """File named for one ID but declaring another is caught (dup/unknown)."""
    job_dir, manifest = _build_job(tmp_path, count=2)
    resp_dir = _write_responses(tmp_path, manifest)
    # img-2.json now declares img-1 -> duplicate of img-1 mapping.
    (resp_dir / "img-2.json").write_text(
        json.dumps(_decision_payload("img-1", 1)), encoding="utf-8"
    )

    with pytest.raises(SinglePassError):
        analyze_job_single_pass(manifest, job_dir, _config(resp_dir))

    assert not (job_dir / "analysis-records.json").exists()


def test_manual_response_missing_image_id_not_system_bound(tmp_path):
    """WO-023 requirement 5: a missing image_id is rejected, never inserted."""
    from lr_ai_exposure.providers.manual_app import (
        analyze_single_image_manual_app,
    )

    job_dir, manifest = _build_job(tmp_path, count=1)
    entry = manifest.entries[0]
    payload = _decision_payload(entry.image_id, 1)
    del payload["image_id"]
    resp = tmp_path / "no-id.json"
    resp.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SinglePassError, match="Missing image_id"):
        analyze_single_image_manual_app(
            entry=entry,
            preview_full_path=job_dir / entry.preview_path,
            response_file=resp,
        )
