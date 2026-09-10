from __future__ import annotations

import hashlib
import json
from pathlib import Path

import lr_ai_exposure.production_job as production


def _policy() -> dict[str, float]:
    return {
        "quantum_ev": 0.05,
        "maximum_delta_ev": 3.0,
        "minimum_exposure2012": -5.0,
        "maximum_exposure2012": 5.0,
    }


def test_fresh_measurement_hash_binds_normalized_output_not_pre_orientation_source(
    monkeypatch, tmp_path: Path
) -> None:
    job_dir = tmp_path / "runtime" / "jobs" / "job-1"
    job_dir.mkdir(parents=True)
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
    production.create_production_job_state(
        job_dir,
        job_id="job-1",
        source_folder="D:/album",
        ordered_image_ids=("1",),
        policy=_policy(),
    )
    production.update_production_job_state(job_dir, production.PLAN_READY)
    production.update_production_job_state(job_dir, production.APPLYING_CATALOG)
    production.update_production_job_state(
        job_dir,
        production.VERIFYING_RENDERS,
        applied_verified_count=1,
        applied_verified_image_ids=["1"],
    )

    normalized = job_dir / "fresh-previews" / "000001__1.jpg"
    normalized.parent.mkdir(parents=True)
    normalized_bytes = b"normalized-oriented-preview"
    normalized.write_bytes(normalized_bytes)
    normalized_sha = hashlib.sha256(normalized_bytes).hexdigest()

    monkeypatch.setattr(production, "snapshot_cache_dbs", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        production,
        "extract_batch",
        lambda *args, **kwargs: [
            {
                "status": "FOUND",
                "id_local": "1",
                "source_preview_tier": 1440,
                "source_preview_sha256": "pre-orientation-source-sha",
                "output": str(normalized),
                "orientation": "DA",
            }
        ],
    )
    monkeypatch.setattr(
        production,
        "measure_production_fresh_previews",
        lambda *args, **kwargs: [
            {
                "image_id": "1",
                "measurement_kind": "ROBUST_SCENE_LUMINANCE",
                "source_preview_sha256": normalized_sha,
                "observed_measurement": 0.5,
            }
        ],
    )

    result = production.extract_and_measure_production_fresh_previews(
        job_dir,
        lrdata_dir=tmp_path / "Catalog Previews.lrdata",
        expected_image_ids=["1"],
        target_preview_size=1440,
    )

    assert result["extract_results"][0]["source_preview_sha256"] == "pre-orientation-source-sha"
    assert result["extract_results"][0]["preview_sha256"] == normalized_sha
    assert result["items"][0]["source_preview_sha256"] == normalized_sha
