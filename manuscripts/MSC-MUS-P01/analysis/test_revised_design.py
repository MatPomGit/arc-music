import unittest
import numpy as np
from scipy.stats import t
from revised_design import cr2, endpoint_design, endpoint
from longitudinal_checks import design


class RevisedDesignTests(unittest.TestCase):
    def test_cr2_single_observation_cluster_hc2(self):
        rng=np.random.default_rng(9)
        x=np.column_stack([np.ones(80),rng.normal(size=80)])
        y=x@np.array([.5,-.4])+rng.normal(size=80)
        c=np.array([0.,1.])
        a,r,df=cr2(x[:,None,:],y[:,None],np.ones((80,1),bool),c)
        b=np.linalg.inv(x.T@x)
        beta=b@x.T@y
        h=np.einsum('ij,jk,ik->i',x,b,x)
        v=x@b@c
        se=np.sqrt(np.sum(v*v*(y-x@beta)**2/(1-h)))
        self.assertAlmostEqual(a,beta[1],places=10)
        self.assertAlmostEqual(r,t.ppf(.98,df)*se,places=10)
    def test_hidden_outcomes_invariant(self):
        x,y,g,c,m,_,_=design(np.random.default_rng(42),'h6',80,8,0.,'mar')
        def f(y): return cr2(x.reshape(80,8,-1),y.reshape(80,8),m.reshape(80,8),c)
        np.testing.assert_array_equal(f(np.where(m,y,np.nan)),f(np.where(m,y,1e9)))
    def test_endpoint_rejects_invalid_inputs(self):
        z,y0,y1,m=endpoint_design(np.random.default_rng(42),80,.85,-.35,'none')
        invalid=z.copy()
        invalid[0]=2
        with self.assertRaises(ValueError): endpoint(invalid,y0,y1,m)
        with self.assertRaises(ValueError): endpoint(z,y0,y1,m.astype(int))
        with self.assertRaises(ValueError): endpoint(z,y0,y1[:-1],m)
        bad=y1.copy()
        bad[0]=np.nan
        with self.assertRaises(ValueError): endpoint(z,y0,bad,m)

    def test_endpoint_complete_oracle(self):
        z,y0,y1,m=endpoint_design(np.random.default_rng(42),80,.85,-.35,'none')
        a,r=endpoint(z,y0,y1,m)
        d=y1-y0
        self.assertAlmostEqual(a,d[z==1].mean()-d[z==0].mean(),places=10)
        self.assertGreater(r,0.)
    def test_endpoint_hidden_outcomes_and_delta(self):
        z,y0,y1,m=endpoint_design(np.random.default_rng(42),800,.85,-.35,'mar')
        a,r=endpoint(z,y0,y1,m)
        np.testing.assert_array_equal((a,r),endpoint(z,y0,np.where(m,y1,1e9),m))
        b,_=endpoint(z,y0,y1,m,(0.,.5))
        self.assertAlmostEqual(b-a,.5*(~m[z==1]).mean(),places=10)
        y0[0]=np.nan
        with self.assertRaises(ValueError): endpoint(z,y0,y1,m)

if __name__=='__main__': unittest.main()
