# Computational illustrations of AIM-ER

Run from this directory using Python 3.10 or later; no external dependencies or data are required.

```sh
python3 -m unittest -v
python3 simulate.py --seed 1729
```

The script prints three synthetic scenarios corresponding to the identification subsection of the manuscript. All coefficients are illustrative; no participant information is used. The output is not an empirical estimate or a power calculation. The seed fixes pseudo-random draws; floating-point results can differ slightly across Python builds.

For normal-theory recruitment sensitivity and Monte Carlo checks, run `python3 power.py`. The assumptions and numerical examples are described in the manuscript.

Extended diagnostics require Python 3.11+ and the pinned NumPy/SciPy environment in `requirements.txt`. Run `python design_checks.py --seed 1729` within a checked-out Git repository for a JSON report containing HEAD, runtime versions, bias, rejection, coverage and Monte Carlo uncertainty. Diary and novelty scenarios are deliberately reduced models; informative loss is a stress test, not a correction. CI uses the checked-out PR head and publishes the report alongside the PDF.

## Extended H6/H8/H10 stress diagnostics

Run `OPENBLAS_NUM_THREADS=1 python longitudinal_checks.py --seed 1730 --reps 300`. This evaluates population-average regressions with cluster-robust uncertainty under random intercepts/slopes, AR(1), heterogeneous residuals, H6 lagged baseline distress and rumination, H10 nonlinear time and monotone dropout, and H8 continuous expertise with baseline covariates. H10 effect is the first-to-last change in the between-arm contrast, with the nonlinear basis zero at endpoints. H6 centring uses all scheduled observed predictors for retrospective association, not prospective prediction. Outcome missingness is simulated, not predictor missingness. The observed-weighted estimator uses the known MAR mechanism in the DGP rather than estimating propensity; oracle weights under MNAR use unavailable latent variables. Neither is an operational cure for MNAR. Differential pattern-mixture shifts are point sensitivity, not valid multiple-imputation intervals. The full mixed-model likelihood with estimated covariance, unknown propensity, missing predictors and prospective prediction is not implemented. Report bias, coverage, null rejection/power, valid replications and MCSE. Final protocol requires recalculation with justified parameters and selected estimator.

Local preliminary check (300 replicates, seed 1729 for H6/H10, 1730 for H8, NumPy/SciPy): H6 MNAR available-case bias about -.047, oracle -.003; H10 MAR available-case bias about .149 vs observed-mechanism weighting .029; H10 MNAR available-case bias about .162 vs observed-mechanism weighting .077. H8 null rejection .057. These are synthetic scenario-specific diagnostics, not participant outcomes. CI will report a separate exact-HEAD seed.
