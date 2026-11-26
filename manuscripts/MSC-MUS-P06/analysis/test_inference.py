import unittest
import numpy as np
import pandas as pd
from inference import fit_arrays, eligible_rows, primary
from simulation import draw,run_cell

class TestP06(unittest.TestCase):
    def test_invariance_to_participant_intercepts(self):
        g,x,y=draw(np.random.default_rng(42),80,6,.3)
        a=fit_arrays(g,x,y)
        b=fit_arrays(g,x,y+100*g)
        np.testing.assert_allclose(a["estimate"],b["estimate"],atol=1e-10)
        np.testing.assert_allclose(a["se"],b["se"],atol=1e-10)

    def test_recovery(self):
        g,x,y=draw(np.random.default_rng(9),1000,10,.3,missing=0)
        self.assertAlmostEqual(fit_arrays(g,x,y)["estimate"][0],.3,delta=.05)

    def test_rank_deficiency(self):
        g,x,y=draw(np.random.default_rng(1),80,6,0)
        x[:,0]=g
        with self.assertRaisesRegex(ValueError,"rank deficient"):
            fit_arrays(g,x,y)

    def test_singletons_excluded(self):
        g,x,y=draw(np.random.default_rng(3),80,6,.3,missing=0)
        a=fit_arrays(g,x,y)
        b=fit_arrays(np.r_[g,100],np.vstack([x,[1,2,3,4]]),np.r_[y,10])
        self.assertEqual(a,b)

    def fixture(self):
        return pd.DataFrame([dict(participant_id="p",session_id="s",
          local_day="2026-11-01",eligible_first=True,activity_defined=True,
          pre_time="2026-11-01T10:00:00+01:00",
          post_time="2026-11-01T10:30:00+01:00",
          followup_time="2026-11-02T10:30:00+01:00",
          avoidance=5,distress_pre=4,expected_difficulty=3,study_day=1,
          interference=2)])

    def test_timing(self):
        d=self.fixture()
        self.assertEqual(len(eligible_rows(d)),1)
        d.loc[0,"followup_time"]="2026-11-03T10:30:00+01:00"
        self.assertEqual(len(eligible_rows(d)),0)

    def test_timezone_required(self):
        d=self.fixture()
        d.loc[0,"pre_time"]="2026-11-01T10:00:00"
        with self.assertRaisesRegex(ValueError,"Timezone"):
            eligible_rows(d)

    def test_invalid_score(self):
        d=self.fixture()
        d.loc[0,"avoidance"]=11
        with self.assertRaisesRegex(ValueError,"Invalid score"):
            eligible_rows(d)

    def test_duplicate_day(self):
        d=pd.concat([self.fixture(),self.fixture()],ignore_index=True)
        d.loc[1,"session_id"]="s2"
        with self.assertRaisesRegex(ValueError,"one eligible"):
            eligible_rows(d)

    def test_simulation_reproducibility(self):
        a=run_cell(np.random.default_rng(8),80,4,.3,.3,"mar",8)
        b=run_cell(np.random.default_rng(8),80,4,.3,.3,"mar",8)
        self.assertEqual(a,b)
        self.assertEqual(a["valid"]+a["failures"],8)

if __name__=="__main__":
    unittest.main()
