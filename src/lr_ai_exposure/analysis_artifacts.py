"""Canonical analysis evidence records — WO-023.

One ``AnalysisRecord`` binds a complete, validated ``SinglePassDecision``
to the provider evidence that produced it: provider name, model, mode,
preview identity (byte count + SHA-256), the response reference that
supplied the decision, and token usage when the provider reports it.

Records are serialized deterministically (stable pydantic field order,
``model_dump(mode="json")``) and written atomically beside the other
canonical job artifacts as ``analysis-records.json``.

No XMP, RAW, catalog, or preview-cache file is ever touched here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lr_ai_exposure.ai_judge import SinglePassDecision
from lr_ai_exposure.analysis_result import _atomic_write_json

__all__ = [
    "AnalysisRecord",
    "serialize_analysis_records",
    "write_analysis_records",
]

ANALYSIS_RECORDS_FILENAME = "analysis-records.json"


class AnalysisRecord(BaseModel):
    """Complete decision plus preserved provider evidence for one image."""

    model_config = ConfigDict(strict=True, extra="forbid")

    decision: SinglePassDecision
    provider: str
    model: str
    mode: str
    preview_bytes: int = Field(..., ge=0)
    preview_sha256: str
    response_reference: str
    token_usage: dict[str, int] | None = None


def serialize_analysis_records(
    job_id: str,
    records: list[AnalysisRecord],
) -> dict[str, Any]:
    """Build the canonical ``analysis-records.json`` payload.

    Records are serialized in the order given (manifest order). The full
    ``SinglePassDecision`` schema — including risk flags, rationales,
    ``batch_consistency_group`` and ``reason`` — is preserved through
    ``model_dump(mode="json")``; no provider metadata field is dropped.
    """
    return {
        "job_id": job_id,
        "record_count": len(records),
        "records": [r.model_dump(mode="json") for r in records],
    }


def write_analysis_records(
    job_dir: Path,
    job_id: str,
    records: list[AnalysisRecord],
) -> Path:
    """Write ``analysis-records.json`` atomically into ``job_dir``."""
    payload = serialize_analysis_records(job_id, records)
    return _atomic_write_json(Path(job_dir) / ANALYSIS_RECORDS_FILENAME, payload)
