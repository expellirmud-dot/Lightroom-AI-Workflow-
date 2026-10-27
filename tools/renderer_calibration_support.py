"""Read-only fail-closed numeric support gate for historical renderer calibration.

This module does NOT apply Lightroom Exposure, accept photographs, or prove
renderer/preset/camera identity. An unsupported target must remain UNRESOLVED.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable, Sequence


class CalibrationOutOfSupport(ValueError):
    """A measurement cannot safely use these calibration observations."""


@dataclass(frozen=True)
class CalibrationSupport:
    baseline_min: float
    baseline_max: float
    rendered_min: float
    rendered_max: float
    sample_count: int


def check_numeric_calibration_support(
    calibration_samples: Sequence[tuple[float, float, float]],
    *,
    baseline_measurement: float,
    target_measurement: float,
) -> CalibrationSupport:
    """Reject extrapolation outside observed baselines and rendered measurements.

    This is a necessary numeric guard only. It is NOT sufficient to establish
    that the historical calibration samples share camera/preset/process/ROI.
    """
    if any(not isfinite(float(v)) or float(v) <= 0
           for v in (baseline_measurement, target_measurement)):
        raise CalibrationOutOfSupport("INVALID_MEASUREMENT")
    pairs = []
    for sample in calibration_samples:
        try:
            before, after, applied_ev = map(float, sample)
        except (TypeError, ValueError) as exc:
            raise CalibrationOutOfSupport("INVALID_CALIBRATION_SAMPLE") from exc
        if not all(isfinite(v) for v in (before, after, applied_ev)):
            raise CalibrationOutOfSupport("INVALID_CALIBRATION_SAMPLE")
        if before <= 0 or after <= 0 or abs(applied_ev) <= 1e-12:
            raise CalibrationOutOfSupport("INVALID_CALIBRATION_SAMPLE")
        if (after - before) * applied_ev <= 0:
            raise CalibrationOutOfSupport("NON_MONOTONIC_CALIBRATION_SAMPLE")
        pairs.append((before, after))
    if len(pairs) < 2 or len({p[0] for p in pairs}) < 2:
        raise CalibrationOutOfSupport("INSUFFICIENT_CALIBRATION")
    low = min(x[0] for x in pairs)
    high = max(x[0] for x in pairs)
    rendered_min = min(min(x) for x in pairs)
    rendered_max = max(max(x) for x in pairs)
    if not low <= float(baseline_measurement) <= high:
        raise CalibrationOutOfSupport("BASELINE_OUTSIDE_CALIBRATION_SUPPORT")
    if not rendered_min <= float(target_measurement) <= rendered_max:
        raise CalibrationOutOfSupport("TARGET_OUTSIDE_CALIBRATION_SUPPORT")
    return CalibrationSupport(low, high, rendered_min, rendered_max, len(pairs))


def estimate_if_supported(
    estimator: Callable[..., float],
    *,
    calibration_samples: Sequence[tuple[float, float, float]],
    baseline_measurement: float,
    target_measurement: float,
    quantum_ev: float,
    max_abs_ev: float,
) -> float:
    """Delegates to the existing EV estimator ONLY after numeric support check.

    Must be combined with renderer/preset/ROI provenance and photographic
    acceptance before ever being integrated into a mutation-capable workflow.
    """
    check_numeric_calibration_support(
        calibration_samples,
        baseline_measurement=baseline_measurement,
        target_measurement=target_measurement,
    )
    return float(estimator(
        calibration_samples=calibration_samples,
        baseline_measurement=baseline_measurement,
        target_measurement=target_measurement,
        quantum_ev=quantum_ev,
        max_abs_ev=max_abs_ev,
    ))
