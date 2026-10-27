"""Non-photographic contract regressions for the RCV-001 evidence audit."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from photographic_gate_audit import EvidenceError, audit_exposure_evidence


class ReviewGateAuditTest(unittest.TestCase):
    def base(self):
        run = {
            "sample_photos": 3,
            "worker_verdict_counts": {"KEEP": 3, "DARKEN": 0},
            "nexus_review_flags": [
                {"n": 8, "stem": "PTO_9197", "verdict": "REVIEW_TOO_BRIGHT_POSSIBLE"}
            ],
            "fresh_photographer_truth_for_sample": False,
        }
        review = {
            "owner_photographic_acceptance": False,
            "items": [{"n": 8, "photo": "PTO_9197", "direction_gate": "DARKEN"}],
        }
        return run, review

    def test_known_all_keep_conflict_blocks(self):
        run, review = self.base()
        r = audit_exposure_evidence(run, review)
        self.assertEqual(r["status"], "BLOCKED_PHOTOGRAPHIC_PROMOTION")
        self.assertEqual(len(r["confirmed_review_conflicts"]), 1)
        self.assertIn("ALL_KEEP_CONTRADICTS_INDEPENDENT_REVIEW", r["reasons"])
        self.assertFalse(r["photographic_quality_certified_by_script"])

    def test_missing_owner_truth_also_blocks_without_conflict(self):
        run, review = self.base()
        run["nexus_review_flags"] = []
        r = audit_exposure_evidence(run, review)
        self.assertNotIn("ALL_KEEP_CONTRADICTS_INDEPENDENT_REVIEW", r["reasons"])
        self.assertIn("PHOTOGRAPHER_ACCEPTANCE_MISSING", r["reasons"])

    def test_owner_evidence_does_not_become_auto_photo_certification(self):
        run, review = self.base()
        run["nexus_review_flags"] = []
        run["fresh_photographer_truth_for_sample"] = True
        review["owner_photographic_acceptance"] = True
        r = audit_exposure_evidence(run, review)
        self.assertEqual(r["status"], "NO_CONFLICT_FOUND_OWNER_EVIDENCE_RECORDED")
        self.assertFalse(r["photographic_quality_certified_by_script"])

    def test_missing_identity_fails_closed(self):
        run, review = self.base()
        review["items"][0]["photo"] = "OTHER"
        with self.assertRaises(EvidenceError):
            audit_exposure_evidence(run, review)

    def test_incomplete_worker_coverage_fails_closed(self):
        run, review = self.base()
        run["worker_verdict_counts"]["KEEP"] = 2
        with self.assertRaises(EvidenceError):
            audit_exposure_evidence(run, review)


if __name__ == "__main__":
    unittest.main()
