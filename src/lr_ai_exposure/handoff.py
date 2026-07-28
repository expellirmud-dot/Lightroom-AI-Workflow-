import os
import json
import uuid
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
from lr_ai_exposure.job import create_job_directory, write_manifest, Manifest, ManifestEntry
from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch

def handoff_job(runtime_root: str, lrdata_dir: str, selection_json_path: str) -> str:
    """
    Takes a selection.json written by Lightroom, creates a job directory,
    snapshots the cache, extracts the previews, and writes manifest.json.
    Returns the job_id.
    """
    runtime_path = Path(runtime_root)
    with open(selection_json_path, "r", encoding="utf-8") as f:
        selection = json.load(f)
        
    job_id = selection.get("job_id", f"job-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    job_dir = create_job_directory(runtime_path, job_id)
    
    # Snapshot cache
    snapshot_dir = job_dir / "cache_snapshots"
    snapshot_cache_dbs(lrdata_dir, str(snapshot_dir))
    
    # Extract previews
    out_dir = job_dir / "previews"
    identities = selection.get("photos", [])
    
    results = extract_batch(identities, str(snapshot_dir), str(out_dir))
    
    # Build manifest entries
    entries = []
    for i, res in enumerate(results):
        src_path = identities[i].get("path", "")
        stem = os.path.splitext(os.path.basename(src_path))[0]
        ext = os.path.splitext(src_path)[1]
        
        # Manifest paths must be relative to job_dir to pass job.py validation
        raw_path_rel = f"{stem}{ext}"
        xmp_path_rel = f"xmp_backups/{stem}.xmp"
        preview_path_rel = f"previews/{i+1:06d}__{stem}.jpg"
        
        status = res["status"]
        preview_bytes = 0
        
        if status == "FOUND" and res.get("output") and os.path.exists(res.get("output", "")):
            preview_bytes = os.path.getsize(res["output"])
            # Ensure every FOUND preview path exists
            if not (job_dir / preview_path_rel).exists():
                raise FileNotFoundError(f"Extracted preview missing at expected relative path: {preview_path_rel}")
            
        entry = ManifestEntry(
            image_id=str(identities[i].get("id_local", "")),
            raw_path=raw_path_rel,
            xmp_path=xmp_path_rel,
            preview_path=preview_path_rel,
            seq=i + 1,
            extraction_status=status,
            uuid=res.get("uuid"),
            preview_bytes=preview_bytes
        )
        entries.append(entry)
        
    manifest = Manifest(job_id=job_id, entries=entries)
    write_manifest(job_dir, manifest)
    
    return job_id
