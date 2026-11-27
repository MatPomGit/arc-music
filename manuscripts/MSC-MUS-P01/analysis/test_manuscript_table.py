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

class ManuscriptStructure(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def expanded(self, name, stack=()):
        if name in stack:
            self.fail(f'Recursive input: {name}')
        source = (self.root / name).read_text(encoding='utf-8')
        return re.sub(
            r'\\(?:input|include)\{([^}]+)\}',
            lambda m: self.expanded(
                m[1] if Path(m[1]).suffix else m[1] + '.tex',
                stack + (name,)),
            source)

    def test_article_and_supplement_are_self_contained(self):
        bibliography = (self.root / 'references.bib').read_text(encoding='utf-8')
        keys = re.findall(r'@\w+\s*\{\s*([^,\s]+),', bibliography)
        self.assertEqual(len(keys), len(set(keys)))
        all_citations = set()
        for name in ('main.tex', 'supplement.tex'):
            with self.subTest(document=name):
                source = self.expanded(name)
                labels = re.findall(r'\\label\{([^}]+)\}', source)
                refs = re.findall(r'\\(?:ref|eqref|autoref|pageref)\{([^}]+)\}', source)
                self.assertEqual(len(labels), len(set(labels)))
                self.assertFalse(set(refs) - set(labels))
                citations = set()
                for group in re.findall(
                    r'\\(?:cite\w*|parencite|textcite)(?:\[[^\]]*\])*\{([^}]+)\}', source
                ):
                    citations.update(key.strip() for key in group.split(','))
                self.assertFalse(citations - set(keys))
                all_citations.update(citations)
        self.assertEqual(all_citations, set(keys))

    def test_hypotheses_and_supplement_sections(self):
        article = (self.root / 'main.tex').read_text(encoding='utf-8')
        supplement = (self.root / 'supplement.tex').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'\\item\[H(\d+):', article),
                         [str(n) for n in range(1, 11)])
        self.assertEqual(len(re.findall(r'(?m)^\\section\{', supplement)), 6)
        self.assertIn(r'\renewcommand{\thesection}{S\arabic{section}}', supplement)
        self.assertNotIn(r'\input{sections/power.tex}', article)
        self.assertIn(r'\input{sections/power.tex}', supplement)


if __name__ == '__main__':
    unittest.main()
