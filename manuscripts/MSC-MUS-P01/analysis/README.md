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

## Gaussian mixed likelihood and estimated observation probabilities

`OPENBLAS_NUM_THREADS=1 python mixed_checks.py --reps 20` profiles a Gaussian likelihood over correlated random intercept/slope covariance, residual AR(1), and log-linear residual SD modifier (observed baseline distress or arm). H6 conditions on scheduled observed predictors and H10 uses a quadratic basis vanishing at endpoints. The likelihood uses only observed outcomes. Fixed-effect model-based intervals condition on fitted covariance; finite-sample and misspecification performance must be assessed, and convergence failures and boundary solutions are reported. This is a working Gaussian model, not an assertion that the DGP exactly satisfies the covariance model or that random effects are independent of all covariates in real data.

Estimate observation probabilities from observed predictors for H6 and discrete-time retention hazard from prior observed outcome and arm for H10. Clip cumulative probability at .025; record sensitivity to clipping in any final protocol. Bootstrap resamples participants and refits the marginal outcome and observation regressions, giving percentile intervals for IPW and fixed-delta marginal pattern mixtures. Those intervals do not account for uncertainty about the unidentifiable delta itself; the model for missing outcomes is conditional on observed covariates, not a fully Bayesian joint model. IPW sandwich Monte Carlo intervals do not account for fitted propensity; bootstrap intervals do. Low replicate count is a smoke diagnostic, not precision certification. Increase simulation replicates and investigate convergence before protocol lock. No participant effects estimated.
