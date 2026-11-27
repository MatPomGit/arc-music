import unittest
from unittest.mock import patch
import numpy as np
from model_comparison import MODELS, reference, summary, cell


class ModelComparisonTests(unittest.TestCase):
    def test_incomplete_records_report_all_models(self):
        x=np.zeros((40,35));x[:10,0]=np.nan
        r=reference(x)
        self.assertEqual([x["model"] for x in r],list(MODELS))
        self.assertTrue(all(x["status"]=="INSUFFICIENT_COMPLETE" for x in r))

    def test_failures_retained_in_denominator(self):
        rows=[{"cfa":[{"model":m,"status":s} for m,s in zip(MODELS,("PROPER","IMPROPER","ERROR"))]},
              {"cfa":[{"model":m,"status":"PROPER"} for m in MODELS]}]
        out=summary(rows)
        self.assertEqual(out["one_factor"]["proper"],2)
        self.assertEqual(out["correlated_seven"]["proper_rate"],.5)
        self.assertEqual(out["higher_order"]["status_counts"]["ERROR"],1)

    def test_independent_efa_cfa_samples(self):
        seen=[]
        def efa(x,*args):
            seen.append(x.copy())
            return {"joint_recovery":False}
        def cfa(x):
            self.assertFalse(np.array_equal(x,seen[-1]))
            return [{"model":m,"status":"PROPER"} for m in MODELS]
        with patch("model_comparison.assess",side_effect=efa), patch("model_comparison.reference",side_effect=cfa):
            out=cell(100,.65,.35,False,0.,2,20,123)
        self.assertEqual(out["requested"],2)
        self.assertEqual(len(seen),2)
