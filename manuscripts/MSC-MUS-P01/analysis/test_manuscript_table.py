"""Regression: the manuscript's recruitment table must agree with code."""
import re
import unittest
from pathlib import Path
from power import plan

class ManuscriptTable(unittest.TestCase):
    def test_recruitment_table(self):
        text = (Path(__file__).resolve().parents[1] / 'sections' / 'power.tex').read_text(encoding='utf-8')
        table = text.split(r'\label{tab:power}', 1)[1].split(r'\end{table}', 1)[0]
        rows = re.findall(r'(?m)^\s*(\.\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*(\d+)\s*\\\\', table)
        self.assertEqual([float(r[0]) for r in rows], [.2,.3,.4,.5])
        for effect, *values in rows:
            expected = [plan(float(effect), k, r2=r)[1] for k in (2,4) for r in (0.,.25)]
            self.assertEqual(list(map(int,values)), expected)

if __name__ == '__main__':
    unittest.main()
