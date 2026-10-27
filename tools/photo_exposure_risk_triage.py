"""Fast read-only exposure *review* escalation from real rendered JPEGs.

Flags unusually bright/dark *display-domain* distributions for human/vision
review. Never infers EV, passes photography, or writes to Lightroom/XMP.
Thresholds are exploratory and require unseen-image validation.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import math
from typing import Any
import numpy as np
from PIL import Image, UnidentifiedImageError


class TriageEvidenceError(ValueError):
    pass


def audit_selection(selection: dict[str, Any], *, bright_fraction: float=0.15,
                    dark_median: float=80.0) -> dict[str, Any]:
    if (not math.isfinite(bright_fraction) or not 0 <= bright_fraction <= 1 or
        not math.isfinite(dark_median) or not 0 <= dark_median <= 255):
        raise TriageEvidenceError("INVALID_THRESHOLDS")
    if not isinstance(selection, dict) or not isinstance(selection.get("rows"),list):
        raise TriageEvidenceError("INVALID_SELECTION")
    root_str=selection.get("source_package")
    if not isinstance(root_str,str) or not root_str:
        raise TriageEvidenceError("MISSING_SOURCE_PACKAGE")
    package=Path(root_str).resolve()
    preview_root=(package/"previews").resolve()
    expected=selection.get("sample_count")
    rows=selection["rows"]
    if type(expected)!=int or expected!=len(rows):
        raise TriageEvidenceError("SAMPLE_COVERAGE_MISMATCH")
    seen_ids=set()
    results=[]
    for row in rows:
        if not isinstance(row,dict):
            raise TriageEvidenceError("INVALID_ROW")
        image_id=str(row.get("image_id",""))
        digest=row.get("sha256")
        if not image_id or image_id in seen_ids:
            raise TriageEvidenceError("IMAGE_ID_DUPLICATE_OR_MISSING")
        seen_ids.add(image_id)
        if not isinstance(digest,str) or len(digest)!=64:
            raise TriageEvidenceError("BAD_SHA256")
        try:
            path=Path(row["preview_path"]).resolve()
            path.relative_to(preview_root)
            payload=path.read_bytes()
        except (OSError,ValueError,KeyError) as exc:
            raise TriageEvidenceError("SOURCE_PREVIEW_UNSAFE_OR_UNREADABLE") from exc
        if hashlib.sha256(payload).hexdigest()!=digest:
            raise TriageEvidenceError("SOURCE_PREVIEW_HASH_MISMATCH")
        try:
            with Image.open(io.BytesIO(payload)) as img:
                if img.format!="JPEG":
                    raise TriageEvidenceError("NOT_JPEG")
                pixels=np.asarray(img.convert("RGB"),dtype=np.uint8)
        except (OSError,UnidentifiedImageError,ValueError) as exc:
            raise TriageEvidenceError("CORRUPT_JPEG") from exc
        rgb=pixels.astype(np.float32)
        luma=0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2]
        median=float(np.median(luma))
        hi=float(np.mean(np.max(pixels,axis=2)>=245))
        flags=[]
        if hi>=bright_fraction:
            flags.append("DISPLAY_HIGHLIGHT_RISK_REVIEW")
        if median<=dark_median:
            flags.append("DISPLAY_SHADOW_RISK_REVIEW")
        results.append({
            "image_id":image_id, "stem":str(row.get("raw_stem","")),
            "source_preview_sha256":digest, "luma_median":round(median,2),
            "fraction_any_rgb_ge245":round(hi,5),
            "outcome":"REVIEW_REQUIRED" if flags else "NO_AUTOMATIC_RISK_FLAG",
            "flags":flags,
        })
    return {
        "status":"READ_ONLY_EXPOSURE_RISK_TRIAGE",
        "accepted_as_photographic_quality":False,
        "numeric_ev_authority":"NONE",
        "catalog_xmp_mutation_authority":"NONE",
        "thresholds":{"bright_fraction":bright_fraction,"dark_median":dark_median},
        "total":len(results),
        "review_required":sum(bool(r["flags"]) for r in results),
        "items":results,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selection",required=True,type=Path)
    p.add_argument("--bright-fraction",type=float,default=0.15)
    p.add_argument("--dark-median",type=float,default=80.0)
    args=p.parse_args()
    try:
        selected=json.loads(args.selection.read_text(encoding="utf-8"))
        report=audit_selection(selected,bright_fraction=args.bright_fraction,dark_median=args.dark_median)
    except (TriageEvidenceError,ValueError,OSError) as exc:
        print(json.dumps({"status":"INVALID_EVIDENCE","reason":str(exc)}))
        return 3
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 2 if report["review_required"] else 0


if __name__=="__main__":
    raise SystemExit(main())
