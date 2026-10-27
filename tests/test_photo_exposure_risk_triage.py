"""RCV-002 review-only histogram risk triage regression tests."""
import hashlib
import io
import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "tools"))
from photo_exposure_risk_triage import audit_selection,TriageEvidenceError


class TestExposureRiskTriage(unittest.TestCase):
    def setup_case(self,colors=(255,10,128)):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        preview_root=root/"previews"
        preview_root.mkdir()
        rows=[]
        for i,value in enumerate(colors):
            out=io.BytesIO()
            Image.new("RGB",(20,20),(value,value,value)).save(out,format="JPEG")
            payload=out.getvalue()
            path=preview_root/f"{i}.jpg"
            path.write_bytes(payload)
            rows.append({"n":i+1,"image_id":str(i+1),"raw_stem":f"PHOTO_{i}",
                         "preview_path":str(path),"sha256":hashlib.sha256(payload).hexdigest()})
        return {"sample_count":len(rows),"source_package":str(root),"rows":rows}

    def test_bright_dark_mid(self):
        report=audit_selection(self.setup_case())
        self.assertEqual(report["review_required"],2)
        self.assertEqual([x["outcome"] for x in report["items"]],
                         ["REVIEW_REQUIRED","REVIEW_REQUIRED","NO_AUTOMATIC_RISK_FLAG"])
        self.assertFalse(report["accepted_as_photographic_quality"])
        self.assertEqual(report["numeric_ev_authority"],"NONE")

    def test_sha_mismatch(self):
        selection=self.setup_case()
        selection["rows"][0]["sha256"]="0"*64
        with self.assertRaisesRegex(TriageEvidenceError,"HASH_MISMATCH"):
            audit_selection(selection)

    def test_duplicate_id(self):
        selection=self.setup_case()
        selection["rows"][1]["image_id"]=selection["rows"][0]["image_id"]
        with self.assertRaisesRegex(TriageEvidenceError,"DUPLICATE"):
            audit_selection(selection)

    def test_disallow_path_escape(self):
        selection=self.setup_case()
        selection["rows"][0]["preview_path"]=str(Path(selection["source_package"])/"other.jpg")
        with self.assertRaisesRegex(TriageEvidenceError,"UNSAFE"):
            audit_selection(selection)

    def test_sample_coverage_mismatch(self):
        selection=self.setup_case()
        selection["sample_count"]+=1
        with self.assertRaisesRegex(TriageEvidenceError,"COVERAGE"):
            audit_selection(selection)


if __name__=="__main__":
    unittest.main()
