# P03 synthetic calibration, 2026-11-26

This is a numerical design check, not participant data. A local Python reproduction of the algorithms in power.py used seed 1729 and 2,000 replicates per scenario (16,000 total), independently calibrating the coefficient from 100,000 synthetic covariate rows per scenario. The latent Gaussian common-factor parameter rho controls association among motives; it is not their exact Pearson correlation. Only outcome missingness under MAR was simulated, with recruitment capped at 560 and 480 complete records as target. All outcomes were bounded 0–10 without clipping. The eight-week cap is not simulated. Exact repository-script execution and independent verification remain pending.

| rho | target partial r | MAR | mean n | target attainment | bias | rejection | coverage |
|---:|---:|:---:|---:|---:|---:|---:|---:|
| .2 | 0 | no | 480 | 1 | -0.000080 | .0545 | .9455 |
| .2 | 0 | yes | 479.964 | .9900 | 0.000293 | .0465 | .9535 |
| .2 | .15 | no | 480 | 1 | -0.000063 | .9015 | .9595 |
| .2 | .15 | yes | 479.9685 | .9895 | 0.000932 | .9110 | .9470 |
| .6 | 0 | no | 480 | 1 | -0.000612 | .0555 | .9445 |
| .6 | 0 | yes | 479.9675 | .9915 | -0.001351 | .0560 | .9440 |
| .6 | .15 | no | 480 | 1 | 0.000557 | .9085 | .9590 |
| .6 | .15 | yes | 479.966 | .9900 | -0.000059 | .9055 | .9495 |

Rejection rates under the alternative are 90.15–91.10%; under the null 4.65–5.60%. Coverage is 94.00–95.95%. Monte Carlo error near power .90 is approximately .0067 (standard error), so results do not establish that actual power is at least .90 in all scenarios. Retain the planning target pending additional non-linear, discrete response, missing predictor and MNAR checks. Calibration is conditional on the specified design; it does not estimate effects in the target population.

## Reproduction

From this directory, with Python 3.11+ and NumPy, pandas, SciPy and statsmodels installed:

```sh
python -m unittest -v
python power.py --seed 1729 --reps 2000 --out power-results.json
python models.py synthetic.csv --data-kind synthetic --out model-results.json
```

The third command expects a separately generated CSV following the survey data contract. Never commit empirical row-level records. The test suite creates its own synthetic fixtures. The model program implements complete-record H1–H4 with HC3, partial correlations, explicit rank checks and Holm correction. MI, ordinal models and nonlinear sensitivity remain planned, not implemented in this stage. No recruitment or preregistration is authorised by this report.
