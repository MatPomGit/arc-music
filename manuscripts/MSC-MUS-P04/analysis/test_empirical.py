import copy
import unittest
import numpy as np
from empirical import cohort, run, component_flow


def fixture(n=80):
    rng=np.random.default_rng(42)
    rows=[]
    for i in range(n):
        rows.append({"study_token":f"p04-00000000-0000-4000-8000-{i:012x}",
             "assignment":i%2,"paq_s_total":int(rng.integers(6,43)),
             "expression_ease":int(rng.integers(0,11)),"clarity_t0":int(rng.integers(0,11)),
             "distress_t0":int(rng.integers(0,11)),"prior_ai_music":int(rng.integers(0,2)),
             "scenario_mode":rng.choice(["personal_mild","fictional"]),
             "meaningful_sketch":1,"fit_t1":int(rng.integers(0,11)),
             "clarity_t1":int(rng.integers(0,11)),"fit_missing_reason":""})
    rows[0]["paq_s_total"]=6; rows[1]["paq_s_total"]=42
    return rows,[{k:r[k] for k in ("study_token","assignment")} for r in rows]


class EmpiricalTests(unittest.TestCase):
    def test_bounds_and_same_cohort(self):
        rows,ledger=fixture()
        out=run(rows,ledger,m=3)
        self.assertEqual(out["n_assigned"],80)
        self.assertIn("mar",out["H1"])
        self.assertIn("mar",out["H1_status_informed_sensitivity"])
        self.assertEqual(out["secondary"]["n_randomised"],80)
        self.assertEqual(out["exploratory"]["status"],"EXPLORATORY")
        self.assertFalse(out["confirmatory_authorized"])

    def test_bad_totals(self):
        rows,ledger=fixture()
        for v in (5,43,24.5,np.nan,"",True):
            b=copy.deepcopy(rows); b[0]["paq_s_total"]=v
            with self.assertRaises(ValueError):cohort(b,ledger)

    def test_item_sum_and_missing_item(self):
        rows,ledger=fixture()
        for r in rows:
            r["paq_s_total"]=24
            r.update({f"paq_s_item_{j}":4 for j in range(1,7)})
        self.assertTrue(np.all(cohort(rows,ledger)[1]==24))
        b=copy.deepcopy(rows); b[0]["paq_s_total"]=25
        with self.assertRaises(ValueError):cohort(b,ledger)
        b=copy.deepcopy(rows); b[0]["paq_s_item_1"]=""
        with self.assertRaises(ValueError):cohort(b,ledger)

    def test_ledger_and_covariates(self):
        rows,ledger=fixture()
        for key,value in (("assignment",1),("study_token",rows[1]["study_token"]),
                          ("clarity_t0",11),("prior_ai_music",2),("scenario_mode","unknown")):
            b=copy.deepcopy(rows); b[0][key]=value
            with self.assertRaises(ValueError):cohort(b,ledger)
        with self.assertRaises(ValueError):cohort(rows[1:],ledger)

    def test_composite_states(self):
        rows,ledger=fixture()
        for i,s,f,why in ((0,0,"","undefined"),(1,1,"","unavailable"),(2,"","","unavailable")):
            rows[i].update(meaningful_sketch=s,fit_t1=f,fit_missing_reason=why)
        a,d,c,s,f,y,q=cohort(rows,ledger)
        self.assertEqual(y[0],0)
        self.assertTrue(np.isnan(y[1:3]).all())
        flow=component_flow(a,s,f,y)
        self.assertEqual(flow["0"]["confirmed_absent"],1)
        self.assertEqual(flow["0"]["unknown_status"],1)
        self.assertEqual(flow["1"]["meaningful_rating_missing"],1)
        b=copy.deepcopy(rows); b[2]["fit_t1"]=4
        with self.assertRaises(ValueError):cohort(b,ledger)
        b=copy.deepcopy(rows); b[2]["fit_missing_reason"]="undefined"
        with self.assertRaises(ValueError):cohort(b,ledger)
        for r in rows:r["expressive_success"]=""
        with self.assertRaises(ValueError):cohort(rows,ledger)
