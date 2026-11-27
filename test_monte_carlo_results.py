import json
from pathlib import Path
import tempfile
import unittest
from monte_carlo_runner import load_plan,job
from monte_carlo_results import planned_reps,export_plots

class Results(unittest.TestCase):
    def test_full_counts(self):
        for study,expected in {"P01":1920000,"P03":20000,"P04":96000,"P05":38000,"P06":126000,"P07":232000,"P08":148000,"P09":98000}.items():
            self.assertEqual(sum(planned_reps(study,"full",t) for t in load_plan(study,"full")),expected)
    def test_plots_only_successful_aggregates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"build";out.mkdir()
            dest=Path(tmp)/"results"
            a=job("joint","a.py")
            b=job("bad","b.py")
            (out/"joint.json").write_text(json.dumps({"cells":[{"n":500,"methods":{"A":{"coverage":{"rate":.95},"bias":-.02},"B":{"coverage":{"rate":None}}}}]}))
            self.assertEqual(export_plots([a,b],{"joint":"EXECUTED","bad":"FAILED"},out,dest,"P04","pilot"),1)
            index=json.loads((dest/"plot-index.json").read_text())
            self.assertFalse(index["complete"])
            self.assertEqual(len(index["plots"][0]["panels"]),2)
            self.assertEqual(list(dest.glob("*.svg")),[dest/"mc-summary.svg"])
            self.assertIn("PARTIAL",(dest/"mc-summary.svg").read_text())
            self.assertTrue(all((dest/p["file"]).exists() for p in index["plots"]))
            self.assertEqual(export_plots([a],{"joint":"REUSED"},out,dest,"P04","pilot"),1)

    def test_summary_retains_all_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"build";out.mkdir()
            dest=Path(tmp)/"results";dest.mkdir()
            (dest/"mc-0001.svg").write_text("old")
            (dest/"personal.svg").write_text("keep")
            (dest/"plot-index.json").write_text(json.dumps({"plots":[{"file":"mc-0001.svg"}]}))
            a=job("joint","a.py")
            (out/"joint.json").write_text(json.dumps({"cells":[{"n":100+i,"coverage":.95,"bias":.02} for i in range(65)]}))
            self.assertEqual(export_plots([a],{"joint":"EXECUTED"},out,dest,"P04","full"),1)
            index=json.loads((dest/"plot-index.json").read_text())
            self.assertEqual(len(index["plots"][0]["panels"]),2)
            self.assertTrue(all(len(p["rows"])==65 for p in index["plots"][0]["panels"]))
            self.assertFalse((dest/"mc-0001.svg").exists())
            self.assertTrue((dest/"personal.svg").exists())
            import xml.etree.ElementTree as ET
            ET.parse(dest/"mc-summary.svg")

if __name__=="__main__":unittest.main()
