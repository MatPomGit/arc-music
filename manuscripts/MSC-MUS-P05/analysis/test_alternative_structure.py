import unittest
from unittest.mock import patch
import numpy as np
from alternative_structure import STRUCTURES,generate,factor_covariance
from alternative_model_calibration import cell
from model_comparison import MODELS

class AlternativeStructureTests(unittest.TestCase):
    def test_covariance_and_reproducibility(self):
        for s in STRUCTURES:
            phi=factor_covariance(s)
            np.testing.assert_array_equal(np.diag(phi),np.ones(len(phi)))
            self.assertGreater(np.linalg.eigvalsh(phi).min(),0.)
            a=generate(100,s,np.random.default_rng(42))
            b=generate(100,s,np.random.default_rng(42))
            self.assertEqual(a.shape,(100,35))
            self.assertTrue(np.isin(a,np.arange(5)).all())
            np.testing.assert_array_equal(a,b)
        p=factor_covariance("correlated_seven")
        self.assertNotAlmostEqual(p[0,1]*p[3,4],p[0,3]*p[1,4])
        p=factor_covariance("higher_order")
        self.assertAlmostEqual(p[0,1]*p[3,4],p[0,3]*p[1,4])
    def test_independent_samples_and_truth(self):
        seen=[]
        def efa(x,k,items,*args):
            seen.append(x.copy())
            self.assertEqual((k,items),(1,35))
            return dict(selected=1,correct_count=True,joint_recovery=True)
        def cfa(x):
            self.assertFalse(np.array_equal(x,seen[-1]))
            return [dict(model=m,status="PROPER",p_scaled=.01 if m=="one_factor" else .50) for m in MODELS]
        with patch("alternative_model_calibration.assess",side_effect=efa),patch("alternative_model_calibration.reference",side_effect=cfa):
            result=cell(100,"one_factor",.65,False,0.,2,10,42)
        self.assertEqual(result["efa_correct_count"],2)
        self.assertEqual(result["fit_rejection_diagnostics"]["one_factor"]["rejections"],2)
        self.assertFalse(result["model_selection_authorized"])
