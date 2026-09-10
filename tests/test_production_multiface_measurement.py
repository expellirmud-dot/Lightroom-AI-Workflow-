from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from lr_ai_exposure.hybrid_exposure import CanonicalFixedSkinRoi, FaceSkinFrameResult, FaceSkinMeasurement
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest
import lr_ai_exposure.production_job as production


def _policy() -> dict[str, float]:
    return {
        "quantum_ev": 0.05,
        "maximum_delta_ev": 3.0,
        "minimum_exposure2012": -5.0,
        "maximum_exposure2012": 5.0,
    }


def _ready_job(tmp_path: Path) -> tuple[Path, bytes]:
    job_dir = tmp_path / "runtime" / "jobs" / "job-1"
    preview_dir = job_dir / "previews"
    preview_dir.mkdir(parents=True)
    payload = b"fake-jpeg-baseline"
    preview_path = preview_dir / "000001__1.jpg"
    preview_path.write_bytes(payload)
    sha = hashlib.sha256(payload).hexdigest()
    (job_dir / "selection.json").write_text(
        json.dumps(
            {
                "protocol_version": "2.0",
                "job_id": "job-1",
                "selected_count": 1,
                "source_folder": "D:/album",
                "photos": [
                    {
                        "id_local": "1",
                        "path": "D:/album/1.NEF",
                        "uuid": "uuid-1",
                        "catalog_exposure2012": 0.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_manifest(
        job_dir,
        Manifest(
            job_id="job-1",
            entries=[
                ManifestEntry(
                    image_id="1",
                    raw_path="D:/album/1.NEF",
                    source_xmp_path="D:/album/1.xmp",
                    backup_relative_path="xmp_backups/1.xmp",
                    preview_path="previews/000001__1.jpg",
                    seq=1,
                    extraction_status="FOUND",
                    uuid="uuid-1",
                    preview_bytes=len(payload),
                    preview_sha256=sha,
                    preview_orientation="AB",
                    source_preview_sha256="source-baseline-1",
                    source_preview_tier=1440,
                )
            ],
            total_selected=1,
            total_found=1,
        ),
    )
    production.create_production_job_state(
        job_dir,
        job_id="job-1",
        source_folder="D:/album",
        ordered_image_ids=("1",),
        policy=_policy(),
    )
    semantics_path = tmp_path / "semantics.json"
    semantics_path.write_text(
        json.dumps(
            {
                "protocol_version": "2.0",
                "job_id": "job-1",
                "groups": [
                    {
                        "group_id": "g-1",
                        "status": "REFERENCE_SELECTED",
                        "reference_image_id": "1",
                        "members": [{"image_id": "1", "verdict": "AUTO"}],
                    }
                ],
                "unassigned": [],
            }
        ),
        encoding="utf-8",
    )
    production.import_visual_semantics(job_dir, semantics_path)
    return job_dir, payload


class _MultiFaceMeter:
    def measure_bytes(self, *, image_id: str, jpeg_bytes: bytes) -> FaceSkinFrameResult:
        assert image_id == "1"
        assert jpeg_bytes == b"fake-jpeg-baseline"
        return FaceSkinFrameResult.from_faces(
            image_id=image_id,
            faces=[
                FaceSkinMeasurement("1:face-0", (0, 0, 10, 10), 80, 0.3),
                FaceSkinMeasurement("1:face-1", (20, 0, 30, 10), 90, 0.5),
            ],
        )


def _roi(box: tuple[int, int, int, int]) -> CanonicalFixedSkinRoi:
    return CanonicalFixedSkinRoi(
        canonical_long_edge=1440,
        canonical_width=1440,
        canonical_height=960,
        box=box,
        mask_width=10,
        mask_height=10,
        packed_mask=b"\xaa\xbb",
        skin_pixels=80,
    )


def test_multiface_baseline_and_fresh_measurement_use_same_face_roi_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_dir, _ = _ready_job(tmp_path)

    monkeypatch.setattr(
        production,
        "build_canonical_fixed_skin_roi",
        lambda **kwargs: _roi(tuple(kwargs["box"])),
    )

    baseline_values = {(0, 0, 10, 10): 0.3, (20, 0, 30, 10): 0.5}
    monkeypatch.setattr(
        production,
        "measure_canonical_fixed_skin_roi",
        lambda *, jpeg_bytes, roi: baseline_values[tuple(roi.box)],
    )

    baseline = production.build_production_baseline_measurements(
        job_dir,
        meter=_MultiFaceMeter(),
        canonical_long_edge=1440,
    )

    assert baseline["items"][0]["status"] == "MEASURED"
    assert baseline["items"][0]["measurement"] == pytest.approx(0.4)

    roi_payload = json.loads((job_dir / "measurement-rois.json").read_text(encoding="utf-8"))
    item = roi_payload["items"][0]
    assert item["measurement_strategy"] == "MEDIAN_USABLE_FACES"
    assert [entry["face_id"] for entry in item["face_rois"]] == ["1:face-0", "1:face-1"]
    assert len(item["face_rois"]) == 2

    fresh = tmp_path / "fresh.jpg"
    fresh.write_bytes(b"fresh-render")
    fresh_values = {(0, 0, 10, 10): 0.4, (20, 0, 30, 10): 0.6}
    monkeypatch.setattr(
        production,
        "measure_canonical_fixed_skin_roi",
        lambda *, jpeg_bytes, roi: fresh_values[tuple(roi.box)],
    )

    measured = production.measure_production_fresh_previews(
        job_dir,
        preview_paths={"1": fresh},
        expected_image_ids=("1",),
    )

    assert measured == [
        {
            "image_id": "1",
            "measurement_kind": "CANONICAL_FIXED_ROI_MEDIAN",
            "source_preview_sha256": hashlib.sha256(b"fresh-render").hexdigest(),
            "observed_measurement": pytest.approx(0.5),
        }
    ]
