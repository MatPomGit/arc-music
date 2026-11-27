import unittest
from invariance_family import global_decision
from invariance_family_calibration import summarize

def tests(*p):
    return {k:{"p_value":v} for k,v in zip(
        ("threshold_shape","threshold_loading","threshold_loading_intercept"),p)}


class FamilyTests(unittest.TestCase):
    def test_minimum_p_and_fixed_family(self):
        r=global_decision([.02,.4],tests(.011,.05,.7))
        self.assertFalse(r["any_rejected"])
        r=global_decision([.02,.4],tests(.009,.011,.7))
        self.assertEqual(r["ordered_gate"],"threshold_shape_rejected")
        self.assertEqual(r["rejected_tests"],["threshold_shape","threshold_loading"])
        self.assertAlmostEqual(r["adjusted_p"]["threshold_shape"],.045)
        self.assertFalse(r["confirmatory_authorized"])

    def test_configural_precedence_and_no_uniqueness_claim(self):
        r=global_decision([.001,.7],tests(.002,.004,.3))
        self.assertEqual(r["ordered_gate"],"configural_rejected")
        self.assertIn("threshold_shape",r["rejected_tests"])
        self.assertFalse(r["latent_mean_comparison_authorized"])

    def test_invalid_inputs(self):
        for p in (float("nan"),-1.,1.1):
            with self.assertRaises(ValueError):
                global_decision([p,.5],tests(.5,.5,.5))
        with self.assertRaises(ValueError):
            global_decision([.5,.5],{})

    def test_failures_and_denominators(self):
        rows=[{"replicate":0,"status":"proper","configural_p_values":[.5,.5],
               "tests":tests(.001,.5,.5),"any_gate_rejected":True},
              {"replicate":1,"status":"failure","reason":"fit"}]
        out=summarize({"records":rows,"requested":2,"sizes":[250,250],"scenario":"threshold_dif"})
        self.assertEqual(out["holm_any_operational"]["rate"],.5)
        self.assertEqual(out["holm_any_conditional"]["rate"],1.)
        self.assertEqual(out["holm_target_operational"]["rate"],.5)
        self.assertEqual(out["failure"],1)
