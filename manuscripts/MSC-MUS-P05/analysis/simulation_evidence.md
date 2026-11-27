# Verified synthetic development evidence v0.11.0

2026-11-26. Source: GitHub Actions run 45894186937, head b3590c4adf5d79babb35f903b1c7db0ef5a5c145, artifact 15152208946. Downloaded ZIP SHA-256 verified against GitHub metadata: 2b905e96795d1aadb7ab5be13a3262dece4a1f8e79af4a5abdb5ce292f042d9d. All seven JSON files were read. Results are synthetic development evidence, not data from participants.

| EFA scenario (9 items, fixed true factor count, no parallel analysis) | Proper fits | Mean primary loading bias | Mean assignment accuracy among proper fits |
|---|---:|---:|---:|
| N400, loading .65, rho .35 | 12/12 | -.0011 | 1.000 |
| N500, same structure, skew, 2% MCAR per item | 12/12 | .0099 | 1.000 |
| N400, loading .40, rho .80, skew | 3/12 | -.0476 | .667 |

| Conditional-weight CFA (35 items, N500) | Proper fits | Mean loading bias among proper fits | Mean complete N |
|---|---:|---:|---:|
| Loading .65, rho .35 | 8/8 | .0074 | 500 |
| Same structure, skew, 2% MCAR per item | 8/8 | .0069 | 248.625 |
| Loading .40, rho .80, skew | 0/8 | NA | 500 |

Robust DWLS, eight items, N500, loading .65, rho .35: 30/30 proper; first loading coverage 27/30 (.900; Wilson .744–.965), first factor correlation coverage 23/30 (.767); null rejection 2/30 (.067; Wilson .018–.213). Full 35-item core scenarios yielded 3/3 proper each, insufficient replication. The first-correlation coverage finding blocks a claim of calibrated inference.

Selection sensitivity, N500, 30 replicates per mechanism: mean first-item threshold bias under MAR was .077 for complete records, .011 for MAR IPW; under MNAR .183 complete records, .116 MAR IPW, -.006 for correctly directed +2 tilt. The simulation tilt is not an empirically identified delta.

Invariance, 250 per group, 30 replicates each: all scenarios had 30 proper analyses. Cumulative tests rejected under invariant data at 2/30, 1/30, 2/30; threshold DIF at 27/30 in all tests; loading DIF at 11/30 for threshold/loading test; intercept DIF at 19/30 for all restrictions. Loading/intercept detection is inadequate for a claim of useful power.

Imputation (8 replicates per mechanism, 5 imputations, 20 sweeps): MAR FCS first-loading coverage under MCAR/MAR/MNAR was 8/8, 7/8, 8/8. Mean bias .045, -.019, -.006 respectively. These small counts do not validate FCS or MNAR identification. Under MCAR the +/-1 shifts produced bias .126 and .122 respectively, illustrating sensitivity to wrong delta.

Fit diagnostics, 30 datasets each, all models proper: mean trace-corrected CFI-like for two vs one factor was .9974 vs .8142 (N250, rho .35), .9990 vs .8157 (N500, rho .35), .9996 vs .9874 (N500, rho .80). This custom diagnostic does not establish validated CFI thresholds.

Decision: NO SAMPLE SIZE SELECTED. Full estimator validation, factor-count recovery and high-replication calibration remain required. CI success records execution, not satisfaction of statistical gates. Never report these results as participant observations.

## Full-pool diagnosis and reference comparison, 2026-11-27

The analytic Jacobian and correlated third start were tested on the same conditional-weight datasets as the historical smoke run. Exact generating moments for loading .40 and factor correlation .80 yielded full rank 56/56. The sampled stress condition still had 0/8 proper fits. Of eight replicates, seven converged numerically with active bounds and latent correlation eigenvalues .00023 to .00394. The eighth did not converge at any start within the budget. The seven converged cases had uniqueness above .70 and Jacobian condition numbers of approximately 3,100 to 53,600. The objective differences between starts were below (5\times10^{-8}) in these seven cases. Rerun with `OPENBLAS_NUM_THREADS=1 python cfa_calibration.py --reps 8`.

The paired check used R 4.5.0, lavaan 0.6-19, Python 3.12, NumPy 2.3.5 and SciPy 1.17.0. In both engines factor variances and latent item-response variances are one. Orient signs by the first item of each domain. Python and lavaan estimate their own polychorics and diagonal weights; their robust inference is separately defined. The threshold discrepancy was under (5\times10^{-15}) in all three proper pairs.

| Synthetic sample | Maximum absolute loading difference | Factor correlation difference | SE difference | Python / reference fit-test p |
|---|---:|---:|---:|---:|
| 8 items, N=800, moderate | .00455 | .00116 | .00121 | .351 / .341 |
| 35 items, N=500, moderate | .00586 | .00584 | .00269 | .124 / .130 |
| 35 items, N=500, weak and skewed, seed 69 | .00595 | .02096 | .00505 | .247 / .181 |
| Historical first weak draw, N=500 | unavailable | unavailable | unavailable | unavailable / .792 |

For the historical draw, lavaan converged but its post-check failed (minimum latent covariance eigenvalue −.001322). A nominal fit-test p-value did not rescue the improper solution. Python likewise rejected the fit. These are paired numerical checks and cannot certify coverage or equivalence of WLSMV statistics.

A targeted diagnostic screen used the robust estimator on 72 additional independent datasets, 12 per scenario (base seed 20261126). Use `calibration_grid.py --diagnostic --scenario ID --count 12` with IDs 100 to 105 and aggregate each shard. Below, coverage averages the 56 parameter-wise rates conditional on a proper fit. It is descriptive and the parameters are correlated.

| ID | N | Loading | Factor correlation | Skew | Proper | Mean conditional coverage | Fit-test null rejections among proper |
|---|---:|---:|---:|---|---:|---:|---:|
| 100 | 400 | .65 | .35 | no | 12/12 | .954 | 1/12 |
| 101 | 650 | .65 | .35 | no | 12/12 | .951 | 0/12 |
| 102 | 500 | .40 | .80 | yes | 1/12 | .911 | 0/1 |
| 103 | 800 | .40 | .80 | yes | 4/12 | .955 | 0/4 |
| 104 | 800 | .40 | .35 | yes | 12/12 | .942 | 1/12 |
| 105 | 800 | .65 | .80 | yes | 12/12 | .960 | 0/12 |

At N=800, 4/12 proper fits imply an estimated Monte Carlo standard error of .136 and a Wilson interval of approximately .138 to .609. Even 12/12 proper fits yield a lower Wilson limit of .758. The comparisons point toward the joint difficulty of weak loadings and closely related factors. This screen cannot resolve the full-pool design or justify a sample size.


## Correction of archived ordered-gate aggregation (27 November 2026)

The historical development artifact [15192334440](https://github.com/MatPomGit/arc-music/actions/runs/45990267517/artifacts/15192334440) contains 320 completed fits (16 cells, 20 replications each). The original ZIP SHA-256 is `d4d7052bfaee1d7705844b728e0320d59d122a1938ee59190dbbd64cb8267095`; the original JSON SHA-256 is `06c803939403f1b0c4a58ff00742b32cf8dce4b726736304ce8f5a8869cc1a55`. The archived values of 1.00 in all cells for any ordered gate rejection were affected by a suffix-classification defect. Reaggregation from recorded final statuses, ignoring the erroneous derived Boolean, gives the following counts (denominator 20 throughout, zero estimation failures).

| Group sizes | Invariant | Threshold DIF | Loading DIF | Intercept DIF |
|---|---:|---:|---:|---:|
| 250 + 250 | 3 (0.15) | 17 (0.85) | 14 (0.70) | 17 (0.85) |
| 350 + 150 | 6 (0.30) | 20 (1.00) | 7 (0.35) | 17 (0.85) |
| 400 + 400 | 2 (0.10) | 20 (1.00) | 16 (0.80) | 19 (0.95) |
| 560 + 240 | 2 (0.10) | 20 (1.00) | 9 (0.45) | 18 (0.90) |

Thirteen of 16 historical numerical rates change; three coincide with the corrected rates. No target-specific Wald statistic or p-value is changed. The 20-replication null results are imprecise and do not establish control of the joint type-I error. Any-gate rejection is not target-specific detection, and nonrejection is not proof of invariance. The original archive is not overwritten. Reproduce the comparison with `python3 reaggregate_invariance.py path/to/original.zip` from this directory. The production calibration now separates rejection, nonrejection and estimation failure and reports conditional and unconditional denominators and Wilson intervals. This correction does not change the ordered decision rule or authorize a group comparison or sample size.


## Versioned reference-estimator discrepancy (27 November 2026)

The exact archived comparison [15193905033](https://github.com/MatPomGit/arc-music/actions/runs/45990267517/artifacts/15193905033), ZIP SHA-256 `a8f9289195e1bbfee3a5ebf92c5febb364511c28dfc7cbe77032d4469cf4c12c`, was independently inspected. The workflow job 140476001715 logged Ubuntu 26.04, Python 3.12.16, R 4.5.2-1ubuntu2 and lavaan 0.6.21-1. NumPy and SciPy were pinned to 2.2.6 and 1.15.3 in requirements.txt.

| Seed / draw | Reference | Python | Max loading / correlation / SE difference |
|---|---|---|---|
| 67, 8 items | proper | proper | .00455 / .00116 / .00121 |
| 68, 35 items, moderate | proper | proper | .00495 / .00461 / .00191 |
| 69, 35 items, weak | proper, minimum eigenvalue .01522 | improper | not estimable |
| Historical weak draw | improper, minimum eigenvalue -.05252 | improper | not estimable |

The historical comparison is immutable. The new comparison pins the observed runtime and numerical package versions, hashes the paired input, reports both estimator statuses even when one fails, and uses prospective development tolerances .02 for loadings, factor correlations and thresholds and .01 for standard errors. It requires both moderate cases to agree and all cases to execute, but any weak-case disagreement remains explicit and blocks a claim of full agreement. Different fit-statistic corrections are not required to yield identical p-values. The new execution and reproducibility remain to be verified; content validation and independent samples remain prerequisites.
