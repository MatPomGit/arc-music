import unittest
import numpy as np
import pandas as pd
import json
from models import prepare
from robustness import basis, nonlinear, ordinal, diagnostics, run, threshold_diagnostics
from test_analysis import fixture


class RobustnessTests(unittest.TestCase):
    def test_linear_tails(self):
        for points in ([-3,-2,-1],[11,12,13]):
            np.testing.assert_allclose(np.diff(basis(points),n=2,axis=0),0,atol=1e-12)

    def test_nonlinear_contrasts(self):
        data,_=prepare(fixture())
        result=nonlinear(data)
        self.assertEqual(len(result['pointwise_contrasts']),6)
        self.assertGreater(result['pointwise_contrasts'][-1]['difference'],0)
        self.assertLess(result['pointwise_contrasts'][0]['difference'],0)

    def test_ordinal_count(self):
        data,_=prepare(fixture())
        row=ordinal(data,'H3')
        self.assertEqual(row['categories'],[0,1,2,3])
        self.assertGreater(row['common_odds_ratio'],1)

    def test_threshold_diagnostics_use_all_cumulative_splits(self):
        data,_=prepare(fixture())
        diagnostic=ordinal(data,'H3')['threshold_diagnostics']
        self.assertEqual([r['threshold'] for r in diagnostic['thresholds']],[0,1,2])
        self.assertEqual(diagnostic['estimated_thresholds'],3)
        self.assertFalse(diagnostic['assumption_verified'])
        for row in diagnostic['thresholds']:
            self.assertEqual(row['n_below_or_equal']+row['n_above'],500)
            self.assertIsNotNone(row['beta'])
        json.dumps(diagnostic,allow_nan=False)

    def test_threshold_rare_and_separated_splits(self):
        x=pd.DataFrame({'target':np.arange(100,dtype=float)})
        y=pd.Series(np.r_[np.zeros(1),np.ones(49),np.full(50,2)])
        diagnostic=threshold_diagnostics(y,x,'target')
        self.assertEqual(diagnostic['thresholds'][0]['status'],'insufficient_split')
        self.assertEqual(diagnostic['thresholds'][1]['status'],'not_estimable')
        self.assertEqual(diagnostic['status'],'insufficient_thresholds')
        self.assertFalse(diagnostic['formal_test'])
        json.dumps(diagnostic,allow_nan=False)

    def test_ordinal_continuous_rejected(self):
        data,_=prepare(fixture())
        with self.assertRaises(ValueError):
            ordinal(data,'H1')

    def test_diagnostics_and_recent(self):
        raw=fixture()
        for key in ('clarity_pre','clarity_post','valence_pre','valence_post','resonance'):
            raw[key]=raw[key].round()
        data,_=prepare(raw)
        self.assertTrue(all(v>=1-1e-10 for v in diagnostics(data,'H1')['vif'].values()))
        result=run(raw)
        self.assertEqual(result['recent_H1']['n'],int((raw.recency<=7).sum()))
        self.assertNotIn('error',result['ordinal']['H1'])


if __name__=='__main__':
    unittest.main()
