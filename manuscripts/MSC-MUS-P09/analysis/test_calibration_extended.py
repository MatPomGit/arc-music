import unittest
import numpy as np
from inference import prepare
from calibration_extended import raw_record, run, summary, BOOT_GRID, stress_run


class ExtendedCalibrationTests(unittest.TestCase):
    def test_raw_masks(self):
        for mode in ("independent","selective"):
            frame, masks = raw_record(np.random.default_rng(42), 588, "alternative", mode)
            d = prepare(frame)
            for k, expected in masks.items():
                actual = d[k].to_numpy(bool) if k.startswith("valid") else d[k].notna().to_numpy()
                np.testing.assert_array_equal(actual, expected)
            self.assertTrue(d.target_status2.eq("defined").all())
            self.assertGreater(d.understanding2.isna().sum(), 0)
            self.assertTrue((d.understanding1.isna() & d.distance1.notna()).any())

    def test_summary_separates_interval_failures(self):
        s = summary([dict(contrast=.4,ci=[.1,.8]),dict(contrast=.6,ci=None)],.5,3)
        self.assertEqual(s["point_failures"],1)
        self.assertEqual(s["interval_failures"],2)
        self.assertEqual(s["conditional_coverage"]["rate"],1)
        self.assertAlmostEqual(s["operational_coverage"]["rate"],1/3)

    def test_stress_grid(self):
        result = stress_run(42, 2, 3)
        cells = result["cells"]
        self.assertEqual(len(cells), 48)
        self.assertEqual(len({(c["hypothesis"], c["missingness"], c["effect"],
                               c["n"], c["profile"]) for c in cells}), 48)
        self.assertEqual({c["allocation"] for c in cells}, {"stratified_blocks"})
        self.assertEqual({c["n"] for c in cells}, {434, 588})
        for cell in cells:
            for method in cell["methods"].values():
                self.assertEqual(method["attempted"], 2)
                self.assertEqual(method["point_fits"] + method["point_failures"], 2)
                self.assertEqual(method["intervals"] + method["interval_failures"], 2)
                expected = .5 if cell["hypothesis"] == "H3" and cell["effect"] == "distance_only" else 0.
                self.assertEqual(method["truth"], expected)

    def test_smoke_reproducibility(self):
        a = run(21, 100, 3, 5, 3, smoke=True)
        self.assertEqual(a,run(21,100,3,5,3,smoke=True))
        self.assertEqual(len(a["bootstrap"]),1)
        self.assertEqual(len(a["raw"]),1)
        self.assertEqual(len(BOOT_GRID),12)
        for value in a["bootstrap"][0]["methods"].values():
            self.assertEqual(value["attempted"],3)
            self.assertEqual(value["point_fits"]+value["point_failures"],3)


if __name__ == "__main__":
    unittest.main()
