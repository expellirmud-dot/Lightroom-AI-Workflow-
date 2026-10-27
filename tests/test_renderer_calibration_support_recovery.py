"""RCV-002 isolated tests: invalid calibration never delegates to EV estimator."""
import math
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from renderer_calibration_support import (
    CalibrationOutOfSupport,
    check_numeric_calibration_support,
    estimate_if_supported,
)

SAMPLES = (
    (0.5, 0.55, +0.2),
    (0.6, 0.67, +0.3),
    (0.8, 0.77, -0.15),
)

class TestCalibrationSupport(unittest.TestCase):
    def test_nominal_in_range(self):
        r=check_numeric_calibration_support(SAMPLES,baseline_measurement=0.6,target_measurement=0.65)
        self.assertEqual(r.sample_count,3)
        self.assertEqual(r.baseline_min,0.5)

    def test_low_baseline_rejected(self):
        with self.assertRaisesRegex(CalibrationOutOfSupport,"BASELINE_OUTSIDE"):
            check_numeric_calibration_support(SAMPLES,baseline_measurement=0.3,target_measurement=0.38)

    def test_high_baseline_rejected(self):
        with self.assertRaisesRegex(CalibrationOutOfSupport,"BASELINE_OUTSIDE"):
            check_numeric_calibration_support(SAMPLES,baseline_measurement=0.95,target_measurement=0.85)

    def test_target_outside_support_rejected(self):
        with self.assertRaisesRegex(CalibrationOutOfSupport,"TARGET_OUTSIDE"):
            check_numeric_calibration_support(SAMPLES,baseline_measurement=0.6,target_measurement=0.9)

    def test_nonmonotonic_rejected(self):
        with self.assertRaisesRegex(CalibrationOutOfSupport,"NON_MONOTONIC"):
            check_numeric_calibration_support(((0.5,0.45,+0.2),(0.6,0.65,+0.2)),baseline_measurement=0.5,target_measurement=0.6)

    def test_not_enough_distinct_baselines(self):
        with self.assertRaisesRegex(CalibrationOutOfSupport,"INSUFFICIENT"):
            check_numeric_calibration_support(((0.5,0.55,+0.2),(0.5,0.56,+0.3)),baseline_measurement=0.5,target_measurement=0.55)

    def test_estimator_not_called_when_unsupported(self):
        calls=[]
        def fake_estimator(**kwargs):
            calls.append(kwargs)
            return 0.3
        with self.assertRaises(CalibrationOutOfSupport):
            estimate_if_supported(fake_estimator,calibration_samples=SAMPLES,baseline_measurement=0.3,target_measurement=0.4,quantum_ev=0.05,max_abs_ev=1.0)
        self.assertEqual(calls,[])

    def test_estimator_called_once_when_supported(self):
        calls=[]
        def fake_estimator(**kwargs):
            calls.append(kwargs)
            return 0.2
        r=estimate_if_supported(fake_estimator,calibration_samples=SAMPLES,baseline_measurement=0.6,target_measurement=0.65,quantum_ev=0.05,max_abs_ev=1.0)
        self.assertEqual(r,0.2)
        self.assertEqual(len(calls),1)

    def test_invalid_nan_or_negative(self):
        for val in (float("nan"),float("inf"),-0.1,0.0):
            with self.subTest(val=val), self.assertRaises(CalibrationOutOfSupport):
                check_numeric_calibration_support(SAMPLES,baseline_measurement=val,target_measurement=0.6)

if __name__=="__main__":
    unittest.main()
