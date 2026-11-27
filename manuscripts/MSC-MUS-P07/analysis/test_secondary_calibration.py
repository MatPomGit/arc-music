import unittest
import json
import numpy as np
from secondary_calibration import generate,run

class SecondaryCalibrationTests(unittest.TestCase):
    def test_outcome_specific_masks(self):
        g,models=generate(160,.10,(.4,-.2),"mar",np.random.default_rng(42))
        x,y,m=models["H2"];z,v,n=models["H3"]
        self.assertEqual(len(g),160*21)
        self.assertEqual(z.shape[1],x.shape[1]+1)
        self.assertTrue(np.all((y>=0)&(y<=10)))
        self.assertTrue(np.all((v>=0)&(v<=3)))
        self.assertTrue(np.any(m!=n))
    def test_accounting_and_serialization(self):
        report=run(2,42,True)
        self.assertEqual(len(report["cells"]),4)
        for cell in report["cells"]:
            for model in cell["models"].values():
                self.assertEqual(model["valid"]+model["failed"],2)
                self.assertEqual(model["holm_rejection_operational"]["denominator"],2)
        json.dumps(report,allow_nan=False)

    def test_parallel_reproducibility_and_checkpoint(self):
        import tempfile
        from pathlib import Path
        serial=run(2,42,True)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'secondary.json'
            parallel=run(2,42,True,workers=2,output=path)
            self.assertEqual(serial,parallel)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),parallel)
            self.assertTrue(parallel['complete'])
            with self.assertRaises(FileExistsError):
                run(2,42,True,output=path)

    def test_selected_cell_matches_smoke_seed(self):
        smoke=run(2,42,True)
        from secondary_calibration import scenario_grid
        self.assertEqual(smoke["full_grid_indices"],[scenario_grid().index(s) for s in scenario_grid(True)])
        selected=run(2,42,cell_index=smoke["full_grid_indices"][-1])
        self.assertEqual(selected["cells"][0],smoke["cells"][-1])
        self.assertTrue(selected["screening_only"])
        with self.assertRaises(ValueError):
            run(2,42,cell_index=-1)
