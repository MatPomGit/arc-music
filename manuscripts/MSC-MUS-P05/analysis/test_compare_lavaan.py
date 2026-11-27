"""Validate the order of reference parameters independently of CSV row order."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from compare_lavaan import read_reference, reference_status, classify, screen, TOLERANCES


class ReferenceParameters(unittest.TestCase):
    def test_orders_multi_digit_items_and_factor_pairs(self):
        factors = 3
        items = 4
        rows = ["meta,converged,reference-version,1,NA"]
        for i in range(factors * items):
            item = f"item{i + 1}"
            rows.append(f"=~,factor{i // items + 1},{item},{i + 1},0.1")
            rows.extend(f"|,{item},t{j + 1},{4*i+j},NA" for j in range(4))
        rows += ["~~,factor2,factor3,.23,.05", "~~,factor1,factor3,.13,.05",
                 "~~,factor1,factor2,.12,.05"]
        with TemporaryDirectory() as temp:
            path = Path(temp) / "reference.csv"
            path.write_text("kind,lhs,rhs,value,se\n" + "\n".join(rows), encoding="utf-8")
            meta, estimates, errors, thresholds = read_reference(path, factors, items)
        self.assertEqual(meta["lavaan"], "reference-version")
        np.testing.assert_array_equal(estimates[:12], np.arange(1, 13))
        np.testing.assert_allclose(estimates[12:], [.12, .13, .23])
        np.testing.assert_allclose(errors[12:], [.05, .05, .05])
        np.testing.assert_array_equal(thresholds, np.arange(48))

    def test_reference_status_and_full_gate(self):
        meta = {"converged":1, "post_check":1, "minimum_uniqueness":.2,
                "minimum_factor_eigenvalue":.02}
        self.assertEqual(reference_status(meta), "PROPER")
        self.assertEqual(reference_status(dict(meta, minimum_factor_eigenvalue=.009)), "IMPROPER")
        self.assertEqual(reference_status(dict(meta, converged=0)), "NONCONVERGED")
        agree = {"reference_status":"PROPER","python_status":"PROPER",
                 "agreement": {k:v/2 for k,v in TOLERANCES.items()}, "loading":.65, "rho":.35}
        self.assertEqual(classify(agree), "PAIRED_AGREEMENT")
        agree["classification"] = classify(agree)
        disagree = dict(agree, python_status="IMPROPER",loading=.4,rho=.8)
        disagree["classification"] = classify(disagree)
        self.assertEqual(disagree["classification"],"ADMISSIBILITY_DISAGREEMENT")
        status = screen([agree,disagree])
        self.assertTrue(status["core_agreement"])
        self.assertFalse(status["full_agreement"])
        self.assertFalse(status["model_readiness_authorized"])
        self.assertEqual(classify(dict(agree,reference_status="IMPROPER",python_status="IMPROPER")), "BOTH_IMPROPER")
        self.assertEqual(classify(dict(agree,agreement={})), "PARAMETER_DISAGREEMENT")
        self.assertEqual(classify(dict(agree,reference_status="ERROR")), "EXECUTION_ERROR")


class ReferenceInputArchive(unittest.TestCase):
    def test_roundtrip_and_tamper(self):
        from reference_inputs import write_input,write_manifest,replay
        x=np.random.default_rng(42).integers(0,5,(40,8))
        with TemporaryDirectory() as temp:
            path=Path(temp)
            _,sha=write_input(path,x,2,4,0)
            row=dict(n=40,factors=2,items_per_factor=4,loading=.65,rho=.35,
                     skew=False,seed=42,input_sha256=sha)
            write_manifest(path,[row])
            metadata,restored=next(replay(path))
            np.testing.assert_array_equal(x,restored)
            self.assertEqual(metadata["input_sha256"],sha)
            f=path/"case-00.csv"
            f.write_bytes(f.read_bytes()+b"\n")
            with self.assertRaisesRegex(ValueError,"digest mismatch"):
                list(replay(path))
    def test_invalid_input(self):
        from reference_inputs import encode
        x=np.zeros((40,8));x[0,0]=.5
        with self.assertRaises(ValueError):encode(x,2,4)
        x[0,0]=np.nan
        with self.assertRaises(ValueError):encode(x,2,4)
