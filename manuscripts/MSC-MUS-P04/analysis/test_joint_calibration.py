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

    def test_pure_composite_mar_no_nonresponse_status_capture(self):
        x,low,high=generate(1000,.60,.9,"composite_mar",np.random.default_rng(42))
        y,status=low
        self.assertTrue(np.array_equal(np.isnan(y),np.isnan(status)))
        self.assertTrue(np.isnan(y).any())
        np.testing.assert_array_equal(y,high[0])
        np.testing.assert_array_equal(status,high[1])
        a=estimate(x,y,status,3,42,"baseline_pmm")
        b=estimate(x,y,status,3,42,"status_informed")
        self.assertEqual(a,b)
    def test_added_reference_preserves_legacy_cells(self):
        a=run(2,2,43,True)
        b=run(2,2,43,True,include_composite_mar=True)
        self.assertEqual(a["cells"],b["cells"][:2])
        self.assertEqual(b["cells"][2]["mechanism"],"composite_mar")
        self.assertEqual(b["cells"][2]["methods"]["baseline_pmm"],b["cells"][2]["methods"]["status_informed"])
        json.dumps(b,allow_nan=False)
