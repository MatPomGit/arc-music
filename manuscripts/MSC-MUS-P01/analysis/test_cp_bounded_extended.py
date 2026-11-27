import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from cp_bounded import SCORES,infer
from cp_bounded_extended import design,cell_probabilities,pattern_mixture,simulate_cell,run

class ExtendedCPTests(unittest.TestCase):
    def test_grid(self):
        self.assertEqual(len(design()),2376)
        self.assertEqual(len(set(design())),2376)
        self.assertEqual(len(design(True)),12)
    def test_differential_retention_preserves_truth(self):
        for mechanism in ("mnar_matched","mnar_mismatched"):
            a=cell_probabilities(.5,.3,mechanism,8.,0)
            b=cell_probabilities(.5,.3,mechanism,8.,1)
            for p in (a,b):
                self.assertAlmostEqual(p.sum(),1.)
                self.assertAlmostEqual((p.sum((0,2))*SCORES).sum(),5.3)
            self.assertFalse(np.allclose(a[...,0],b[...,0]))
    def test_no_missing_matches_standardisation(self):
        rng=np.random.default_rng(42)
        observed=rng.multinomial(100,np.ones(11)/11,size=(20,4,2))
        total=observed.sum(-1)
        truth=np.zeros(2)
        a=infer(observed,"standardised",truth)
        b=pattern_mixture(observed,total,truth,(-1.,0.,0.,-1.))
        for key in ("valid","failed","joint"):
            self.assertEqual(a[key],b[key])
        np.testing.assert_allclose(a["bias"],b["bias"],atol=1e-12)
        np.testing.assert_allclose(a["coverage"],b["coverage"])
    def test_accounting_reproducibility(self):
        task=(0,(1600,(0.,.6),.5,"mnar_matched",8.),30,123)
        a=simulate_cell(task)
        self.assertEqual(a,simulate_cell(task))
        self.assertEqual(len(a["methods"]),7)
        for v in a["methods"].values():
            self.assertEqual(v["valid"]+v["failed"],30)
        json.dumps(a,allow_nan=False)
    def test_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"screen.json"
            a=run(4,123,1,True,p)
            b=json.loads(p.read_text(encoding="utf-8"))
            self.assertTrue(b["complete"])
            self.assertEqual(len(b["cells"]),12)
            self.assertEqual(a["cells"],b["cells"])
            with self.assertRaises(FileExistsError):
                run(4,123,1,True,p)
