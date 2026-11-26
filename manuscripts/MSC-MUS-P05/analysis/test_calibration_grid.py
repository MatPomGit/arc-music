import unittest
from calibration_grid import scenarios,aggregate,run

class GridTests(unittest.TestCase):
    def test_grid(self):
        s=scenarios()
        self.assertEqual(len(s),60)
        self.assertEqual(sum(r["kind"]=="core" for r in s),40)
        self.assertEqual(len({r["id"] for r in s}),60)
    def test_duplicate_and_mixed_rejected(self):
        a={"schema":1,"scenario":scenarios()[0],"seed":2,"records":[{"replicate":0,"complete_n":200,"status":"failure"}]}
        with self.assertRaises(ValueError):
            aggregate([a,a])
        b=dict(a,seed=3)
        with self.assertRaises(ValueError):
            aggregate([a,b])
    def test_failure_retained(self):
        a={"schema":1,"scenario":scenarios()[0],"seed":2,"records":[{"replicate":0,"complete_n":5,"status":"failure"}]}
        result=aggregate([a])
        self.assertEqual(result["proper"],0)
        self.assertEqual(result["decision"],"not_calibrated")
    def test_shard_reproducibility(self):
        s=scenarios()[-1]
        a=run(s,0,2); b=run(s,0,1); c=run(s,1,1)
        self.assertEqual(a["records"],b["records"]+c["records"])
        self.assertEqual(aggregate([b,c]),aggregate([a]))

if __name__=="__main__":
    unittest.main()
