# Computational illustrations of AIM-ER

Run from this directory using Python 3.10 or later; no external dependencies or data are required.

```sh
python3 -m unittest -v
python3 simulate.py --seed 1729
```

The script prints three synthetic scenarios corresponding to the identification subsection of the manuscript. All coefficients are illustrative; no participant information is used. The output is not an empirical estimate or a power calculation. The seed fixes pseudo-random draws; floating-point results can differ slightly across Python builds.

For normal-theory recruitment sensitivity and Monte Carlo checks, run `python3 power.py`. The assumptions and numerical examples are described in the manuscript.

Extended diagnostics require Python 3.11+ and the pinned NumPy/SciPy environment in `requirements.txt`. Run `python design_checks.py --seed 1729` within a checked-out Git repository for a JSON report containing HEAD, runtime versions, bias, rejection, coverage and Monte Carlo uncertainty. Diary and novelty scenarios are deliberately reduced models; informative loss is a stress test, not a correction. CI uses the checked-out PR head and publishes the report alongside the PDF.
