import unittest
from monte_carlo_custom import build
from monte_carlo_results import planned_reps

class Custom(unittest.TestCase):
    def test_all_studies(self):
        for study,expected in {"P01":96,"P03":10,"P04":48,"P05":19,"P06":63,"P07":116,"P08":74,"P09":49}.items():
            tasks=build(study,23,123,{})
            self.assertEqual(sum(planned_reps(study,"custom",t) for t in tasks),23*expected)
            self.assertEqual(len({t.name for t in tasks}),len(tasks))
            names={t.name for t in tasks}
            for t in tasks:
                self.assertTrue(set(t.deps)<=names)
                if "--seed" in t.args:self.assertEqual(t.args[t.args.index("--seed")+1],"123")
    def test_partial_shards(self):
        tasks=build("P09",23,9,{"--draws":199},"ipw/cell-06")
        self.assertEqual(len(tasks),3)
        self.assertEqual([planned_reps("P09","custom",t) for t in tasks],[20,3,0])
        self.assertEqual(tasks[-1].args[-1],"23")
    def test_individual_design(self):
        for study,task,d in [
            ("P01","cp-joint",dict(n=400,effect1=.2,effect2=.3,profile="equal")),
            ("P07","primary",dict(n=160,prevalence=.2,effect=.4,missing=.3,mechanism="mar")),
            ("P08","factorial",dict(n=400,authority=.3,interaction=.2,missing=.1,mechanism="mcar",nonadherence=.1))]:
            jobs=build(study,23,123,{},task,d)
            self.assertEqual(len(jobs),1)
            self.assertIn("--design",jobs[0].args)
            self.assertEqual(planned_reps(study,"custom",jobs[0]),23)
        with self.assertRaises(ValueError):
            build("P01",23,123,{},"cp-joint",dict(n=401,effect1=.2,effect2=.3,profile="equal"))
    def test_invalid(self):
        for study,options in [("P03",{"--cap":100}),("P08",{"--reference-n":101}),("P01",{"--n":100})]:
            with self.assertRaises(ValueError):build(study,5,0,options)
        self.assertEqual(build("P02",5,0,{}),[])

if __name__=="__main__":unittest.main()
