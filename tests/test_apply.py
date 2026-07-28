import pytest
import json
from pathlib import Path
from lr_ai_exposure.apply import apply_exposure_deltas
from lr_ai_exposure.ai_judge import SinglePassDecision, Verdict
from lr_ai_exposure.job import Manifest, ManifestEntry, write_manifest

def test_apply_exposure_deltas(tmp_path: Path):
    job_dir = tmp_path / "jobs" / "job_test"
    job_dir.mkdir(parents=True)
    (job_dir / "xmp_backups").mkdir()
    
    # Create fake original XMP
    photos_dir = tmp_path / "photos"
    photos_dir.mkdir()
    xmp_file = photos_dir / "IMG_01.xmp"
    xmp_file.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.00"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n',
        encoding="utf-8"
    )
    
    # Create selection.json
    selection = {
        "job_id": "job_test",
        "photos": [
            {"id_local": 1, "path": str(photos_dir / "IMG_01.CR2")},
            {"id_local": 2, "path": str(photos_dir / "IMG_02.CR2")}, # will be skipped
        ]
    }
    selection_path = tmp_path / "selection.json"
    with open(selection_path, "w", encoding="utf-8") as f:
        json.dump(selection, f)
        
    # Create manifest
    manifest = Manifest("job_test", [
        ManifestEntry("1", "IMG_01.CR2", "xmp_backups/IMG_01.xmp", "previews/1.jpg", 1, "FOUND"),
        ManifestEntry("2", "IMG_02.CR2", "xmp_backups/IMG_02.xmp", "previews/2.jpg", 2, "FOUND"),
    ])
    write_manifest(job_dir, manifest)
    
    # Create decisions
    d1 = SinglePassDecision(
        image_id="1", 
        relevance_verdict=Verdict.KEEP, 
        quality_verdict=Verdict.KEEP, 
        delta_ev=1.5, 
        confidence=0.9, 
        highlight_risk=False, 
        shadow_risk=False, 
        subject_rationale="", 
        scene_rationale="", 
        batch_consistency_group="", 
        reason=""
    )
    d2 = SinglePassDecision(
        image_id="2", 
        relevance_verdict=Verdict.REVIEW, 
        quality_verdict=Verdict.KEEP, 
        delta_ev=1.0, 
        confidence=0.7, 
        highlight_risk=False, 
        shadow_risk=False, 
        subject_rationale="", 
        scene_rationale="", 
        batch_consistency_group="", 
        reason=""
    )
    
    # Run real apply
    results = apply_exposure_deltas(job_dir, selection_path, [d1, d2], dry_run=False, apply_authorized=True)
    
    print(results)
    
    assert results["applied"] == 1
    assert results["skipped"] == 1
    assert results["errors"] == 0
    
    # Check XMP was updated
    assert 'crs:Exposure2012="+1.50"' in xmp_file.read_text(encoding="utf-8")
    
    # Check backup exists
    backups = list((job_dir / "xmp_backups").glob("*.bak"))
    assert len(backups) == 1
