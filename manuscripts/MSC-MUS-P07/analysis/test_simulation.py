import unittest
import numpy as np
from inference import fit_arrays,fit,PRED
from simulation import draw,run,scenarios
import pandas as pd
class TestSimulation(unittest.TestCase):
    def test_production_equivalence(self):
        g,x,y,k,_=draw(np.random.default_rng(42),80,.25,.4,.3,"mar")
        a=pd.DataFrame(x[k],columns=PRED);a["participant_id"]=g[k];a["valence60"]=y[k]
        self.assertEqual(fit(a),fit_arrays(g[k],x[k],y[k]))
    def test_switcher_exclusion(self):
        g,x,y,k,_=draw(np.random.default_rng(4),80,.25,.4,.3,"mar")
        f=fit_arrays(g[k],x[k],y[k])
        extra=np.array([[0,5,5,5,1,12],[0,4,4,4,2,13]])
        self.assertEqual(f,fit_arrays(np.r_[g[k],100,100],np.vstack([x[k],extra]),np.r_[y[k],10,0]))
    def test_bounded_and_stage_missingness(self):
        g,x,y,k,flow=draw(np.random.default_rng(7),160,.25,.4,.3,"mnar")
        self.assertTrue(np.all((y>=0)&(y<=10)&(y%1==0)))
        self.assertTrue(.55<flow["complete"]<.85)
        self.assertTrue(.15<flow["prevalence"]<.35)
    def test_reproducibility(self):
        a=run(reps=2,reference_n=500,seed=3,smoke=True)
        self.assertEqual(a,run(reps=2,reference_n=500,seed=3,smoke=True))
        self.assertTrue(all(c["valid"]+c["failures"]==2 for c in a["cells"]))
    def test_design_grid(self):
        self.assertEqual(len(scenarios()),44)
if __name__=="__main__":unittest.main()
