import unittest
from unittest.mock import patch
import numpy as np
from invariance_reference_calibration import cell,summarize,TRUE_NULLS,SCENARIOS
from invariance_family import NAMES

class InvarianceReferenceTests(unittest.TestCase):
    def test_partial_null_and_failed_denominators(self):
        def row(rejected):
            return {"wlsmv":{"status":"PROPER","decision":{"rejected_tests":rejected,"any_rejected":bool(rejected)}}}
        rows=[row(["threshold_loading"]),row(["threshold_shape","threshold_loading"]),
              {"wlsmv":{"status":"UNAVAILABLE"}}]
        a=summarize(rows,"loading_dif","wlsmv")
        self.assertEqual(a["true_null_fwer_operational"]["count"],1)
        self.assertEqual(a["true_null_fwer_operational"]["denominator"],3)
        self.assertEqual(a["true_null_fwer_conditional"]["denominator"],2)
        self.assertEqual(a["target_rejection_operational"]["count"],2)
        self.assertEqual( set(TRUE_NULLS["intercept_dif"]),set(NAMES[:4]))
    def test_same_input_both_methods_and_replicate_index(self):
        seen=[]
        def local(a,b):
            seen.append((a.copy(),b.copy()))
            return {"status":"PROPER","decision":{"rejected_tests":[],"any_rejected":False}}
        def reference(a,b):
            np.testing.assert_array_equal(a,seen[-1][0])
            np.testing.assert_array_equal(b,seen[-1][1])
            return {"status":"PROPER","decision":{"rejected_tests":[],"any_rejected":False}}
        with patch("invariance_reference_calibration.python_reference",side_effect=local),patch("invariance_reference_calibration.reference",side_effect=reference):
            result=cell(0,"invariant",2,123,offset=4)
        self.assertEqual([r["replicate"] for r in result["records"]],[4,5])
        self.assertEqual(result["paired_available"],2)
        self.assertFalse(np.array_equal(seen[0][0],seen[1][0]))

    def test_order_independent_pairing_and_strict_aggregation(self):
        from invariance_reference_calibration import summarize_cell,aggregate
        def row(i):
            def fit(names):
                return {"status":"PROPER","decision":{"rejected_tests":names,"any_rejected":True}}
            return {"replicate":i,"python":fit(["threshold_shape","threshold_loading"]),
                    "wlsmv":fit(["threshold_loading","threshold_shape"])}
        a=summarize_cell(0,"threshold_dif",42,0,[row(0)])
        b=summarize_cell(0,"threshold_dif",42,1,[row(1)])
        result=aggregate([b,a],2)
        self.assertEqual(result["paired_identical_rejection_sets"]["count"],2)
        self.assertEqual(result["paired_test_decisions"]["threshold_shape"]["both_reject"],2)
        self.assertTrue(result["precision_screen_only"])
        for bad in ([a],[a,a],[a,dict(b,seed=43)],[a,dict(b,offset=0)]):
            with self.assertRaises(ValueError):aggregate(bad,2)
