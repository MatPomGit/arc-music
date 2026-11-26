import unittest
import numpy as np
from simulation import draw
from stress import selection,scenarios,run
class TestStress(unittest.TestCase):
    def test_monotone_dropout(self):
        rng=np.random.default_rng(42)
        _,x,_,_,_=draw(rng,500, .1,.4,0,"mar")
        e,t,r=selection(rng,x,500,21,.45)
        r=r.reshape(500,21)
        self.assertTrue(r[:,0].all())
        self.assertTrue((np.diff(r.astype(int),axis=1)<=0).all())
        self.assertTrue(.45<r[:,-1].mean()<.65)
        self.assertTrue(.80<e.mean()<.90)
        self.assertTrue(.86<t.mean()<.94)
    def test_no_selection(self):
        rng=np.random.default_rng(4)
        _,x,_,_,_=draw(rng,80,.1,.4,0,"mar")
        self.assertTrue(all(v.all() for v in selection(rng,x,80,21,0,ongoing=0,timing=0)))
    def test_grid(self):
        self.assertEqual(len(scenarios(160)),12)
        self.assertEqual(len(scenarios(320)),12)
    def test_reproducibility_and_denominators(self):
        a=run(n=160,reps=2,reference_n=500)
        self.assertEqual(a,run(n=160,reps=2,reference_n=500))
        for c in a["cells"]:
            self.assertEqual(c["valid"]+c["failures"],2)
            self.assertLessEqual(c["unconditional_rejection"],c["valid_fraction"])
            self.assertLessEqual(c["mean_switchers"],160)
if __name__=="__main__":unittest.main()
