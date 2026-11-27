import unittest
import numpy as np
from scipy.stats import t
from revised_design import cr2, endpoint_design, endpoint, summary
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
    def test_cr2_multisession_deleted_rows_oracle(self):
        rng = np.random.default_rng(451)
        groups, sessions = 18, 5
        x = np.stack([np.ones((groups, sessions)),
                      rng.normal(size=(groups, sessions))], axis=-1)
        y = x @ np.array([.3, -.25]) + rng.normal(size=(groups, 1)) + rng.normal(size=(groups, sessions))
        mask = rng.random((groups, sessions)) > .2
        mask[0] = False
        c = np.array([0., 1.])
        actual = cr2(x, y, mask, c)
        # Independent dense reference: physically delete missing rows,
        # construct the full residual-maker and adjusted score vectors.
        X, Y = x[mask], y[mask]
        B = np.linalg.inv(X.T @ X)
        beta = np.linalg.lstsq(X, Y, rcond=None)[0]
        M = np.eye(len(Y)) - X @ B @ X.T
        residual = M @ Y
        scores, vectors = [], []
        offset = 0
        for n in mask.sum(axis=1):
            if n == 0:
                continue
            idx = slice(offset, offset+n)
            eigen, U = np.linalg.eigh(M[idx, idx])
            A = U @ np.diag(1 / np.sqrt(eigen)) @ U.T
            v = np.zeros(len(Y))
            v[idx] = A @ X[idx] @ B @ c
            scores.append(v @ residual)
            vectors.append(M @ v)
            offset += n
        gram = np.asarray(vectors) @ np.asarray(vectors).T
        df = np.trace(gram)**2 / np.sum(gram**2)
        radius = t.ppf(.98, df) * np.linalg.norm(scores)
        np.testing.assert_allclose(actual, [c @ beta, radius, df], rtol=1e-10)

    def test_cr2_rejects_malformed_inputs(self):
        x = np.ones((8, 3, 1))
        y = np.ones((8, 3))
        m = np.ones((8, 3), dtype=bool)
        c = np.ones(1)
        with self.assertRaises(ValueError):
            cr2(x, y, m.astype(int), c)
        with self.assertRaises(ValueError):
            cr2(x, y[:, :-1], m, c)
        with self.assertRaises(ValueError):
            cr2(x, y, m, np.array([np.nan]))
        y[0, 0] = np.nan
        with self.assertRaises(ValueError):
            cr2(x, y, m, c)

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
        for shifts in ((0.,), (0., np.nan), (0., 0., 0.)):
            with self.assertRaises(ValueError):
                endpoint(z,y0,y1,m,shifts)
        bad=y1.copy()
        bad[0]=np.nan
        with self.assertRaises(ValueError): endpoint(z,y0,bad,m)

    def test_summary_retains_failed_replications(self):
        empty = summary([], 0., 10)
        self.assertEqual((empty['valid'], empty['failed']), (0, 10))
        self.assertIsNone(empty['coverage'])
        self.assertIsNone(empty['bias_mcse'])
        single = summary([(0., 1.)], 0., 10)
        self.assertEqual((single['valid'], single['failed']), (1, 9))
        self.assertEqual(single['coverage'], 1.)
        self.assertIsNone(single['bias_mcse'])
        mixed = summary([(0., 1.), (2., .5)], 0., 10)
        self.assertEqual(mixed['failed'], 8)
        self.assertEqual(mixed['coverage'], .5)
        self.assertEqual(mixed['rejection'], .5)
        with self.assertRaises(ValueError):
            summary([(np.nan, 1.)], 0., 10)
        with self.assertRaises(ValueError):
            summary([(0., -1.)], 0., 10)

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
