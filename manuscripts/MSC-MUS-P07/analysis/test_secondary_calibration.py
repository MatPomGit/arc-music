import unittest
import json
import numpy as np
from secondary_calibration import generate,run

class SecondaryCalibrationTests(unittest.TestCase):
    def test_outcome_specific_masks(self):
        g,models=generate(160,.10,(.4,-.2),"mar",np.random.default_rng(42))
        x,y,m=models["H2"];z,v,n=models["H3"]
        self.assertEqual(len(g),160*21)
        self.assertEqual(z.shape[1],x.shape[1]+1)
        self.assertTrue(np.all((y>=0)&(y<=10)))
        self.assertTrue(np.all((v>=0)&(v<=3)))
        self.assertTrue(np.any(m!=n))
    def test_accounting_and_serialization(self):
        report=run(2,42,True)
        self.assertEqual(len(report["cells"]),4)
        for cell in report["cells"]:
            for model in cell["models"].values():
                self.assertEqual(model["valid"]+model["failed"],2)
                self.assertEqual(model["holm_rejection_operational"]["denominator"],2)
        json.dumps(report,allow_nan=False)
