import unittest
import numpy as np
from models import prepare
from robustness import basis, nonlinear, ordinal, diagnostics, run
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
