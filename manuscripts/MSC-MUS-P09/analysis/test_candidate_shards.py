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

    def test_paired_candidate_shards(self):
        from compare_candidates import shard as paired_shard,summarize,run
        def generate(rng,*args,**kwargs):return {"x":float(rng.random())}
        def report(d,reps,seed):
            return {"hypotheses":{h:{"contrast":d["x"],"candidate_available":True,
                "candidate_ci":[-1.,1.],"candidate_p":.5,"attempted":reps,
                "successful":reps,"failed":0} for h in ("H1","H2","H3")},
                "candidate_secondary_holm":{"H2":1.,"H3":1.}}
        with patch("compare_candidates.generate",side_effect=generate),patch("compare_candidates.candidate_family",side_effect=report),patch("compare_candidates.augmented_family",side_effect=report):
            a=paired_shard(6,0,1,199,123)
            b=paired_shard(6,1,1,199,123)
            result=run(6,2,199,123)
        self.assertEqual(summarize([b,a],2),result)
        self.assertEqual(result["paired_comparison"]["H1"]["both_available"],2)
        self.assertEqual(result["paired_comparison"]["H1"]["mean_squared_error_difference_aipw_minus_ipw"],0.)
        self.assertFalse(result["confirmatory_authorized"])
        json.dumps(result,allow_nan=False)
        for parts in ([a],[a,a],[a,dict(b,seed=124)],[a,dict(b,offset=0)]):
            with self.assertRaises(ValueError):summarize(parts,2)
