from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from pathlib import Path

import pytest

from PIL import Image

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
    selection = {
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
    (job_dir / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
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


class _SingleFaceMeter:
    def measure_bytes(self, *, image_id: str, jpeg_bytes: bytes) -> FaceSkinFrameResult:
        assert image_id == "1"
        assert jpeg_bytes == b"fake-jpeg-baseline"
        return FaceSkinFrameResult.from_faces(
            image_id=image_id,
            faces=[
                FaceSkinMeasurement(
                    face_id="1:face-0",
                    box=(10, 10, 40, 40),
                    skin_pixels=100,
                    measurement=0.4,
                )
            ],
        )


def _roi() -> CanonicalFixedSkinRoi:
    return CanonicalFixedSkinRoi(
        canonical_long_edge=1440,
        canonical_width=1440,
        canonical_height=960,
        box=(10, 10, 40, 40),
        mask_width=30,
        mask_height=30,
        packed_mask=b"\xaa\xbb\xcc",
        skin_pixels=100,
    )


def test_baseline_measurement_builds_and_persists_frozen_canonical_roi(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_dir, _ = _ready_job(tmp_path)
    monkeypatch.setattr(production, "build_canonical_fixed_skin_roi", lambda **kwargs: _roi())
    monkeypatch.setattr(production, "measure_canonical_fixed_skin_roi", lambda **kwargs: 0.42)

    result = production.build_production_baseline_measurements(
        job_dir,
        meter=_SingleFaceMeter(),
        canonical_long_edge=1440,
    )

    assert result["result_kind"] == "DETERMINISTIC_MEASUREMENT_RESULTS"
    assert result["items"][0]["status"] == "MEASURED"
    assert result["items"][0]["measurement"] == pytest.approx(0.42)
    roi_payload = json.loads((job_dir / "measurement-rois.json").read_text(encoding="utf-8"))
    assert roi_payload["result_kind"] == "PRODUCTION_CANONICAL_FIXED_ROIS"
    assert roi_payload["items"][0]["image_id"] == "1"
    assert roi_payload["items"][0]["roi"]["packed_mask_base64"] == "qrvM"
    assert production.load_production_job_state(job_dir)["baseline_measurements"] == "measurement-results.json"


def test_baseline_measurement_persists_backend_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_dir, _ = _ready_job(tmp_path)
    monkeypatch.setattr(production, "build_canonical_fixed_skin_roi", lambda **kwargs: _roi())
    monkeypatch.setattr(production, "measure_canonical_fixed_skin_roi", lambda **kwargs: 0.42)
    provenance = {
        "backend": "YOLO_FACE_PLUS_HSV_SKIN",
        "model_path": "models/yolov8n-face.pt",
        "model_sha256": "D17B38523A994B13EE604B67F02791CA0F43B9F446A32FD7BC44E17C56EAD077",
        "confidence": 0.55,
        "iou": 0.45,
        "image_size": 1024,
        "min_skin_pixels": 50,
        "selected_device": "cpu",
        "dependency_versions": {
            "torch": "2.0.0",
            "ultralytics": "8.0.0",
        },
    }

    result = production.build_production_baseline_measurements(
        job_dir,
        meter=_SingleFaceMeter(),
        canonical_long_edge=1440,
        measurement_provenance=provenance,
    )

    roi_payload = json.loads((job_dir / "measurement-rois.json").read_text(encoding="utf-8"))
    assert result["measurement_provenance"] == provenance
    assert roi_payload["measurement_provenance"] == provenance


def test_fresh_measurement_reuses_frozen_roi_and_returns_adjusted_subset_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_dir, _ = _ready_job(tmp_path)
    monkeypatch.setattr(production, "build_canonical_fixed_skin_roi", lambda **kwargs: _roi())
    monkeypatch.setattr(production, "measure_canonical_fixed_skin_roi", lambda **kwargs: 0.42)
    production.build_production_baseline_measurements(
        job_dir,
        meter=_SingleFaceMeter(),
        canonical_long_edge=1440,
    )

    fresh = tmp_path / "fresh-1.jpg"
    fresh.write_bytes(b"fresh-render-generation")
    observed_rois: list[CanonicalFixedSkinRoi] = []

    def fake_measure(*, jpeg_bytes: bytes, roi: CanonicalFixedSkinRoi) -> float:
        assert jpeg_bytes == b"fresh-render-generation"
        observed_rois.append(roi)
        return 0.47

    monkeypatch.setattr(production, "measure_canonical_fixed_skin_roi", fake_measure)
    result = production.measure_production_fresh_previews(
        job_dir,
        preview_paths={"1": fresh},
        expected_image_ids=("1",),
    )

    assert result == [
        {
            "image_id": "1",
            "measurement_kind": "CANONICAL_FIXED_ROI",
            "source_preview_sha256": hashlib.sha256(b"fresh-render-generation").hexdigest(),
            "observed_measurement": 0.47,
        }
    ]
    assert observed_rois == [_roi()]


def test_baseline_measurement_fails_closed_when_preview_sha_does_not_match_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job_dir, _ = _ready_job(tmp_path)
    manifest_path = job_dir / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["entries"][0]["preview_sha256"] = "wrong"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(production, "build_canonical_fixed_skin_roi", lambda **kwargs: _roi())
    monkeypatch.setattr(production, "measure_canonical_fixed_skin_roi", lambda **kwargs: 0.42)

    with pytest.raises(production.ProductionJobError, match="preview_sha256"):
        production.build_production_baseline_measurements(job_dir, meter=_SingleFaceMeter())
    assert not (job_dir / "measurement-rois.json").exists()


def test_baseline_measurement_uses_deterministic_median_for_multi_face_frame(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    job_dir, _ = _ready_job(tmp_path)

    class MultiFaceMeter:
        def measure_bytes(self, *, image_id: str, jpeg_bytes: bytes) -> FaceSkinFrameResult:
            return FaceSkinFrameResult.from_faces(
                image_id=image_id,
                faces=[
                    FaceSkinMeasurement("1:face-0", (0, 0, 10, 10), 80, 0.3),
                    FaceSkinMeasurement("1:face-1", (10, 0, 20, 10), 90, 0.4),
                ],
            )

    rois = {
        (0, 0, 10, 10): CanonicalFixedSkinRoi(
            canonical_long_edge=1440,
            canonical_width=1440,
            canonical_height=960,
            box=(0, 0, 10, 10),
            mask_width=10,
            mask_height=10,
            packed_mask=b"\xaa\bb",
            skin_pixels=80,
        ),
        (10, 0, 20, 10): CanonicalFixedSkinRoi(
            canonical_long_edge=1440,
            canonical_width=1440,
            canonical_height=960,
            box=(10, 0, 20, 10),
            mask_width=10,
            mask_height=10,
            packed_mask=bytes([0xCC, 0xDD]),
            skin_pixels=90,
        ),
    }
    monkeypatch.setattr(
        production,
        "build_canonical_fixed_skin_roi",
        lambda **kwargs: rois[tuple(kwargs["box"])],
    )
    values = {(0, 0, 10, 10): 0.3, (10, 0, 20, 10): 0.4}
    monkeypatch.setattr(
        production,
        "measure_canonical_fixed_skin_roi",
        lambda *, jpeg_bytes, roi: values[tuple(roi.box)],
    )

    result = production.build_production_baseline_measurements(job_dir, meter=MultiFaceMeter())
    assert result["items"][0]["status"] == "MEASURED"
    assert result["items"][0]["measurement"] == pytest.approx(0.35)
    roi_payload = json.loads((job_dir / "measurement-rois.json").read_text(encoding="utf-8"))
    assert roi_payload["items"][0]["measurement_strategy"] == "MEDIAN_USABLE_FACES"
    assert [x["face_id"] for x in roi_payload["items"][0]["face_rois"]] == [
        "1:face-0",
        "1:face-1",
    ]



def _jpeg_bytes(width: int, height: int, *, marker: int) -> bytes:
    image = Image.new("RGB", (width, height), (marker, 80, 40))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=91)
    return out.getvalue()


def _write_lr_preview_cache(
    root: Path,
    *,
    image_id: str,
    uuid: str,
    digest: str,
    data: bytes,
    tier: int = 1440,
    orientation: str = "AB",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    previews_db = root / "previews.db"
    create_table = not previews_db.exists()
    with sqlite3.connect(previews_db) as db:
        if create_table:
            db.execute(
                "CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT, digest TEXT, orientation TEXT)"
            )
        db.execute(
            "INSERT INTO ImageCacheEntry VALUES (?, ?, ?, ?)",
            (image_id, uuid, digest, orientation),
        )
    root_db = root / "root-pixels.db"
    create_root = not root_db.exists()
    with sqlite3.connect(root_db) as db:
        if create_root:
            db.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        db.execute("INSERT INTO RootPixels VALUES (?, ?)", (uuid, data))
    bucket = root / uuid[:1] / uuid[:4]
    bucket.mkdir(parents=True, exist_ok=True)
    (bucket / f"{uuid}-{digest}_{tier}").write_bytes(data)


def test_adjusted_only_fresh_preview_extraction_binds_subset_order_tier_and_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "runtime" / "jobs" / "job-1"
    preview_dir = job_dir / "previews"
    preview_dir.mkdir(parents=True)
    baseline_shas: dict[str, str] = {}
    entries = []
    photos = []
    for seq, image_id in enumerate(["1", "2", "3"], start=1):
        baseline = f"baseline-{image_id}".encode("ascii")
        baseline_path = preview_dir / f"{seq:06d}__{image_id}.jpg"
        baseline_path.write_bytes(baseline)
        baseline_sha = hashlib.sha256(baseline).hexdigest()
        baseline_shas[image_id] = baseline_sha
        entries.append(
            ManifestEntry(
                image_id=image_id,
                raw_path=f"D:/album/{image_id}.NEF",
                source_xmp_path=f"D:/album/{image_id}.xmp",
                backup_relative_path=f"xmp_backups/{image_id}.xmp",
                preview_path=f"previews/{seq:06d}__{image_id}.jpg",
                seq=seq,
                extraction_status="FOUND",
                uuid=f"uuid-{image_id}",
                preview_bytes=len(baseline),
                preview_sha256=baseline_sha,
                source_preview_sha256=baseline_sha,
                source_preview_tier=1440,
            )
        )
        photos.append(
            {
                "id_local": image_id,
                "path": f"D:/album/{image_id}.NEF",
                "uuid": f"uuid-{image_id}",
                "catalog_exposure2012": 0.0,
            }
        )
    (job_dir / "selection.json").write_text(
        json.dumps(
            {
                "protocol_version": "2.0",
                "job_id": "job-1",
                "selected_count": 3,
                "source_folder": "D:/album",
                "photos": photos,
            }
        ),
        encoding="utf-8",
    )
    write_manifest(job_dir, Manifest(job_id="job-1", entries=entries))
    production.create_production_job_state(
        job_dir,
        job_id="job-1",
        source_folder="D:/album",
        ordered_image_ids=("1", "2", "3"),
        policy=_policy(),
    )
    production.update_production_job_state(job_dir, production.PLAN_READY)
    production.update_production_job_state(job_dir, production.APPLYING_CATALOG)
    production.update_production_job_state(
        job_dir,
        production.VERIFYING_RENDERS,
        applied_verified_count=2,
        applied_verified_image_ids=["2", "1"],
    )
    (job_dir / "measurement-rois.json").write_text(
        json.dumps(
            {
                "protocol_version": "2.0",
                "result_kind": "PRODUCTION_CANONICAL_FIXED_ROIS",
                "job_id": "job-1",
                "items": [
                    {"image_id": "1", "roi": production._serialize_canonical_fixed_roi(_roi())},
                    {"image_id": "2", "roi": production._serialize_canonical_fixed_roi(_roi())},
                ],
            }
        ),
        encoding="utf-8",
    )
    lrdata = tmp_path / "Catalog Previews.lrdata"
    fresh_bytes: dict[str, bytes] = {}
    for image_id in ["1", "2", "3"]:
        data = _jpeg_bytes(1440, 960, marker=120 + int(image_id))
        fresh_bytes[image_id] = data
        _write_lr_preview_cache(
            lrdata,
            image_id=image_id,
            uuid=f"uuid-{image_id}",
            digest=f"digest-{image_id}",
            data=data,
        )
    monkeypatch.setattr(production, "measure_canonical_fixed_skin_roi", lambda **kwargs: 0.42)

    result = production.extract_and_measure_production_fresh_previews(
        job_dir,
        lrdata_dir=lrdata,
        expected_image_ids=["2", "1"],
        target_preview_size=1440,
    )

    assert [item["image_id"] for item in result["items"]] == ["2", "1"]
    assert [item["image_id"] for item in result["extract_results"]] == ["2", "1"]
    assert all(item["source_preview_tier"] == 1440 for item in result["extract_results"])
    assert result["items"][0]["source_preview_sha256"] == hashlib.sha256(fresh_bytes["2"]).hexdigest()
    assert result["items"][1]["source_preview_sha256"] == hashlib.sha256(fresh_bytes["1"]).hexdigest()
    assert result["items"][0]["source_preview_sha256"] != baseline_shas["2"]
    assert not any((job_dir / "fresh-previews").glob("*__3.jpg"))
    assert not (job_dir / "passes").exists()
    assert not (job_dir / "contact-sheets").exists()
    assert (job_dir / "fresh-measurements.json").is_file()

