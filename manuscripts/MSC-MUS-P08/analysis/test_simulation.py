import unittest
import numpy as np
import pandas as pd
from inference import fit_arrays,fit,BASE
from simulation import draw,run,scenarios
class TestSimulation(unittest.TestCase):
    def test_equivalence(self):
        x,y,k=draw(np.random.default_rng(42),240,.45,.6,"mar")
        d=pd.DataFrame(x[:,4:],columns=BASE)
        d["authority"]=x[:,1]+.5;d["manual"]=x[:,2]+.5
        d["ownership"]=np.where(k[0],y[0],np.nan)
        a=fit(d,"ownership");b=fit_arrays(x[k[0]],y[0][k[0]])
        for key in a:self.assertAlmostEqual(a[key]["beta"],b[key]["beta"],places=10)
    def test_bounds_and_balance(self):
        x,y,k=draw(np.random.default_rng(5),480,.45,.6,"mnar")
        self.assertTrue(all(np.all((v>=0)&(v<=10)) for v in y))
        self.assertTrue(all(np.allclose(v*3,np.rint(v*3)) for v in y))
        self.assertTrue(np.all(np.unique(x[:,1:3],axis=0,return_counts=True)[1]==120))
        self.assertTrue(all(.70<m.mean()<.90 for m in k))
    def test_grid(self):
        self.assertEqual(len(scenarios()),36)
    def test_reproducibility(self):
        a=run(3,400,seed=4,smoke=True)
        self.assertEqual(a,run(3,400,seed=4,smoke=True))
        self.assertTrue(all(c["valid"]==3 for c in a["cells"]))
    def test_invalid_cell(self):
        x,y,k=draw(np.random.default_rng(1),240,.45,.6,"mar")
        with self.assertRaises(ValueError):fit_arrays(x[x[:,1]==.5],y[0][x[:,1]==.5])
if __name__=="__main__":unittest.main()
