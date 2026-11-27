import unittest
from copy import deepcopy
from calibration_targeted import shard, aggregate, MECHANISMS, hc3


class TargetedTests(unittest.TestCase):
    def test_hc3_grid(self):
        r=hc3(2)
        self.assertEqual(len(r["cells"]),8)
        self.assertTrue(all(c["profile"]=="heteroskedastic" for c in r["cells"]))

    def test_shard_reproducibility(self):
        a=shard("MAR",0,2,3)
        self.assertEqual(a,shard("MAR",0,2,3))
        self.assertEqual([r["index"] for r in a["rows"]],[0,1])

    def test_aggregate_requires_every_shard(self):
        parts=[]
        for m in MECHANISMS:
            for i in range(10):
                p=dict(schema_version=1,synthetic=True,seed=20261129,mechanism=m,shard=i,
                       count=2,draws=3,profile="heteroskedastic",effect="null",hypothesis="H1",n=588,
                       rows=[dict(index=j,estimates={"ipw":dict(contrast=.1,ci=[-.2,.4],successful=3,failed=0)},
                                  positivity_warning=False,shift_envelope=True)
                             for j in range(2*i,2*i+2)])
                parts.append(p)
        out=aggregate(parts,count=2,draws=3)
        self.assertEqual(out["outer_per_cell"],20)
        self.assertEqual(out["requested_bootstrap_draws"],120)
        self.assertEqual(out["scenarios"]["MAR"]["methods"]["ipw"]["conditional_coverage"]["rate"],1)
        self.assertEqual(out["scenarios"]["MAR"]["methods"]["shift_0/0"]["point_failures"],20)
        for bad in (parts[:-1],parts+[parts[0]]):
            with self.assertRaises(ValueError): aggregate(bad,count=2,draws=3)
        bad=deepcopy(parts);bad[0]["rows"][1]["index"]=0
        with self.assertRaises(ValueError): aggregate(bad,count=2,draws=3)
        for invalid in (
            dict(successful=4, failed=-1),
            dict(successful=3.0, failed=0),
            dict(contrast=float("nan")),
            dict(ci=[.4,-.2]),
            dict(ci=None),
            dict(successful=2, failed=1),
            dict(ci=[-11,.4]),
        ):
            with self.subTest(invalid=invalid):
                bad=deepcopy(parts)
                bad[0]["rows"][0]["estimates"]["ipw"].update(invalid)
                with self.assertRaises(ValueError):
                    aggregate(bad,count=2,draws=3)


if __name__=="__main__": unittest.main()
