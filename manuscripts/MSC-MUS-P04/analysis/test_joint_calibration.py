import unittest
import json
import numpy as np
from joint_calibration import generate,estimate,run


class JointCalibrationTests(unittest.TestCase):
    def test_paired_status_capture(self):
        x,low,high=generate(660,.60,.9,"status_dependent",np.random.default_rng(42))
        y,s=low; yy,ss=high
        self.assertTrue(np.all(yy[np.isfinite(y)]==y[np.isfinite(y)]))
        self.assertTrue(np.all(ss[np.isfinite(s)]==s[np.isfinite(s)]))
        self.assertLessEqual(np.isnan(ss).sum(),np.isnan(s).sum())
        self.assertTrue(np.all(y[s==0]==0))
        out=estimate(x,y,s,3,42,"status_informed")
        self.assertEqual(len(out["sensitivity"]),27)
        self.assertIn("mar",out)
    def test_small_grid_accounting(self):
        out=run(2,2,42,True)
        self.assertEqual(len(out["cells"]),2)
        for cell in out["cells"]:
            for v in cell["methods"].values():
                self.assertEqual(v["requested"],2)
                self.assertEqual(v["valid"]+v["failed"],2)
        self.assertFalse(out["confirmatory_authorized"])
        json.dumps(out,allow_nan=False)
