import json
import unittest
import numpy as np
from cp_bounded import probabilities,run,SCORES

class BoundedCPTests(unittest.TestCase):
    def test_population_truth_and_bounds(self):
        for centre in (.15,.5,.85):
            for effect in (0.,.3,-.1):
                for mechanism in ("complete","mcar","mar","mnar"):
                    p=probabilities(centre,effect,mechanism,8.)
                    self.assertAlmostEqual(p.sum(),1.)
                    self.assertTrue((p>=0).all())
                    self.assertAlmostEqual((p.sum((0,2))*SCORES).sum(),10*centre+effect)
    def test_reproducibility_and_accounting(self):
        grid=[(420,(0.,.6),.85,m,8.) for m in ("complete","mcar","mar","mnar")]
        a=run(30,3,grid)
        self.assertEqual(a,run(30,3,grid))
        self.assertFalse(a["confirmatory_authorized"])
        for c in a["cells"]:
            self.assertTrue(c["union_null"])
            for v in c["methods"].values():
                self.assertEqual(v["valid"]+v["failed"],30)
                self.assertGreaterEqual(v["joint"],0.)
                self.assertLessEqual(v["joint"],1.)
        self.assertEqual(a["cells"][0]["mean_retention"],1.)
        json.dumps(a,allow_nan=False)
    def test_mar_and_mnar_differ(self):
        p=probabilities(.5,.3,"mar",8.)
        q=probabilities(.5,.3,"mnar",8.)
        ret=p[...,0]/p.sum(-1)
        self.assertTrue(np.allclose(ret,ret[:,:1]))
        self.assertFalse(np.allclose(q[...,0]/q.sum(-1),ret))

if __name__=="__main__":unittest.main()
