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
            self.assertEqual(export_plots([a,b],{"joint":"EXECUTED","bad":"FAILED"},out,dest,"P04","pilot"),2)
            index=json.loads((dest/"plot-index.json").read_text())
            self.assertFalse(index["complete"])
            self.assertTrue(all((dest/p["file"]).exists() for p in index["plots"]))
            self.assertEqual(export_plots([a],{"joint":"REUSED"},out,dest,"P04","pilot"),2)

if __name__=="__main__":unittest.main()
