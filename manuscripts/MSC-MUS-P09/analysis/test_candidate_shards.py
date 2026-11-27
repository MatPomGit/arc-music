import unittest
from unittest.mock import patch
import json
from candidate_shards import shard,aggregate,GRID
from assignment_candidate import point
from missingness import arm_estimates
from inference import prepare
from test_inference import fixture

class ShardTests(unittest.TestCase):
    def test_ipw_only_exact_equivalence(self):
        d=prepare(fixture())
        d.loc[0,"understanding2"]=float("nan")
        old=[arm_estimates(d[d.music==a],"understanding2") for a in (0,1)]
        got,diag=point(d,"understanding2")
        self.assertEqual(got,old[1][0]-old[0][0])
        self.assertEqual(diag,[v[1] for v in old])
        self.assertIsNone(arm_estimates(d[d.music==0],"understanding2",include_shifts=False)[2])
    def test_independent_seed_and_aggregation(self):
        cell=GRID.index((440,"MCAR","null","standard"))
        a=shard(123,cell,0,1,199);b=shard(123,cell,1,1,199)
        self.assertEqual(shard(123,cell,0,2,199)["records"],a["records"]+b["records"])
        result=aggregate([b,a],2)
        self.assertTrue(result["precision_screen_only"])
        self.assertEqual(result["secondary_true_null_fwer"]["denominator"],2)
        self.assertEqual(result["hypotheses"]["H2"]["holm_operational_rejection"]["denominator"],2)
        self.assertFalse(result["confirmatory_authorized"])
        json.dumps(result,allow_nan=False)
        for parts in ([a],[a,a],[a,dict(b,seed=124)]):
            with self.assertRaises(ValueError):aggregate(parts,2)
    def test_no_true_null_not_zero_fwer(self):
        cell=GRID.index((440,"complete","all_positive","standard"))
        a=shard(123,cell,0,1,199)
        self.assertIsNone(aggregate([a],1)["secondary_true_null_fwer"])
