"""Validate the order of reference parameters independently of CSV row order."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from compare_lavaan import read_reference


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
