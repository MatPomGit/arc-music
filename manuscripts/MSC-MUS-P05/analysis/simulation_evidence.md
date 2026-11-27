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


## Global five-test family candidate

The previous ordered gate used two group-fit tests at .025 each and three cumulative restriction tests at .05 each. Nonrejection of a preceding test does not guarantee global error control. The new development candidate applies Holm at family alpha .05 over all five valid p-values, under arbitrary dependence. A significant group-fit test blocks interpretation of the restriction sequence; otherwise the first adjusted rejection is reported. Cumulative tests do not uniquely identify the violated restriction. No latent means are authorized. The old gate and archived outputs remain unchanged. The global control guarantee is conditional on valid individual null p-values; small-sample Wald and model-fit approximations must be calibrated.

Paired retrospective screen from run 46006727066, artifact 15201653027 (ZIP SHA256 ef76147e785f424b1a2a7365adc01b538b07dbf63e5e46129016440718baac53): 20 proper fits per cell.

| Group sizes | Invariant | Threshold DIF | Loading DIF | Intercept DIF |
|---|---:|---:|---:|---:|
| 250 + 250 | 1/20 | 16/20 | 7/20 | 12/20 |
| 350 + 150 | 2/20 | 19/20 | 3/20 | 13/20 |
| 400 + 400 | 0/20 | 20/20 | 8/20 | 17/20 |
| 560 + 240 | 1/20 | 19/20 | 8/20 | 14/20 |

These are any-gate rejections, not unique detection of the generating violation. The paired retrospective screen is not independent validation. Reduced loading-DIF sensitivity remains a problem. The independent-seed driver records the same gate, proper/failed counts, conditional and operational rejection, target cumulative-test rejection, Wilson intervals and Monte Carlo standard errors. Its 20-replicate CI run is an execution screen. Final calibration requires enough independent replications to resolve the intended error rate (e.g. at least 2,000 per intended null configuration; MCSE near .0049 at .05), partial-null configurations and a separately parameterized multigroup ordinal WLSMV reference. No approved group comparison or final sample size follows.

## Exact-input follow-up

Run 46014802772, exact HEAD ca261a622d3f5dcbd71884e1cc7a9af9d9f4dd2b, artifact 15206435600, ZIP SHA-256 687985d666da54936ecbee96a0dcfe08629e80b0206975acb9969b9953c3ac7d. Its JSON matches artifact 15201817166 across all four input hashes, statuses and numerical differences. Artifact 15201807120, despite identical reported Python/NumPy/SciPy/R/lavaan versions and seeds, has different input hashes for seeds 68, 69 and the regenerated historical weak draw; seed 67 matches. The differing seed-69 case is proper in both estimators but correlation difference .020955 exceeds .02. On the repeated input (seed 69 digest ec492886f508b2d175fa9b959e81065c33f3b5e75190c2b0eff277e9dd061d32), lavaan is proper (minimum eigenvalue .015225) and Python improper. Thus cross-run differences cannot be attributed solely to estimators; the cause of input variation is unverified. The new reference-input archive stores actual synthetic CSV bytes and a SHA-256 manifest; replay validates bytes before fitting, not just seed. Historical outputs and generators remain unchanged. Core agreement is not full readiness.

## Paired multigroup ordinal reference candidate

The new `invariance_reference.R` uses semTools 0.5.7 and lavaan WLSMV with theta parameterization, std.lv factor identification and Wu–Estabrook ordinal identification. Fit two separate group configural models and four joint models (configural, equal thresholds, equal thresholds/loadings, equal thresholds/loadings/intercepts). Each cumulative restricted model is compared against the joint configural model using the robust scaled difference test, not subtraction of scaled chi-square statistics. Apply the same five-slot Holm rule as the Python diagnostic to the corresponding p-values. The paired driver uses exactly the same synthetic eight-item data for both methods; archive the input digest, fit failures, test availability, true-null family error and target-specific rejection. In loading-DIF cells configural and threshold nulls remain true; in intercept-DIF cells the threshold/loading nulls also remain true. No latent mean estimates are exported. Initial four-cell smoke crosses invariant and three DIF configurations with unequal groups represented. See https://doi.org/10.1007/s11336-016-9506-0 and https://cran.r-project.org/web/packages/semTools/refman/semTools.html (measEq.syntax). A reference rejection mismatch is not by itself a software defect: the tests differ in estimation and statistic. Full precision and empirical measurement validation remain open.

## Alternative generating structures: executed screen

Artifact 15207725547, run 46017682010 at 0bf50ebaeae35492f5cd7a59847b1b9016396786, ZIP SHA-256 2bdc1c71c6200d1d99803629a413962035249325e3ece0ec6c462a40a22be4d2. At N500, one independent EFA/CFA draw per structure and 10 parallel-analysis permutations: selected factor counts 1/7/7 for one-factor/higher-order/block-correlated seven-factor truth. For one-factor truth only the one-factor WLSMV fit was proper, nonrejected; the two seven-factor alternatives were improper. For higher-order truth all fits were proper, one-factor rejected and both seven-factor models nonrejected. For block-correlated truth all fits were proper, one-factor and higher-order rejected, correlated-seven nonrejected. These are execution examples, not rates, proof of model selection, or empirical validation. One draw per cell and 10 permutations cannot justify measurement structure or sample size.

## Executed paired multigroup screen

Artifact 15206709377, run 46019000181, exact HEAD 3807e440f91da2899a5f0400c8490b113b85fc89; ZIP SHA-256 9226201bf9a97e331a6e7f79820836cbfd397d871ac9483b4ef2e1da2ef551e6. All four Python and WLSMV families were available (20/20 reference test slots). One dataset each: invariant 250+250, neither rejects; loading DIF 350+150, neither rejects; threshold DIF 400+400, Python rejects all three cumulative restrictions, WLSMV only threshold; intercept DIF 560+240, Python none, WLSMV intercept. No observed false true-null rejection in these four draws; not a rate estimate. Set comparison must ignore ordering of Holm rejections. Version 2 corrects this and adds per-test paired discordances plus strict shard aggregation. Use `--size-index 0 --scenario invariant --reps 20 --offset 0` (then disjoint offsets) and `--aggregate folder --expected 40` for two 20-replicate shards, same seed, one cell per folder. Retain exact source HEAD and input-generation environment; do not combine duplicate or mixed-revision shards. Adequate global and partial-null calibration, weak-DIF sensitivity and full-pool extension remain unverified.

## Executed retest precision screen (28 November 2026)

Source HEAD `bf1879598a55a14b8aa73674bfb24d25ca4fbab7`; local Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, single OpenBLAS thread. The four reconstructed source files were checked against Git blob hashes: retest_calibration.py `78e4e49cd27a7cd506a4bf6f6b1d3af2b44a6f94`, retest.py `b547826665321432d4cf774eb5d8c153fb5c25da`, cohort_contract.py `04d7fa36222786dbf78257bd75ff7c275e181bdb`, validity.py `b31e48bda70a5e05cf13c49fabb0165a030203f7`. All matched. Run from analysis/ with `OPENBLAS_NUM_THREADS=1 python retest_calibration.py --reps 100 --boot 199 > screen.json` (default seed 20261128). Local output SHA-256 `253744e606f6fb367919b1920cf74d66731744146bae8d163944b1d822f66b4c`; this digest identifies the local output, not a CI artifact. Runtime differs from the pinned CI dependencies.

| Scenario | Invited | Mean pairs | Available / 100 | Covered / 100 | Bias (available points) | Mean interval width |
|---|---:|---:|---:|---:|---:|---:|
| Stable | 30 | 24.06 | 0 | 0 | NA | NA |
| Stable | 60 | 48.09 | 100 | 84 | .0056 | .4167 |
| Stable | 100 | 79.61 | 100 | 93 | -.0068 | .3582 |
| Stable | 160 | 127.83 | 100 | 94 | .0003 | .2795 |
| Shift | 30 | 23.79 | 0 | 0 | NA | NA |
| Shift | 60 | 47.96 | 100 | 88 | .0034 | .3442 |
| Shift | 100 | 80.77 | 100 | 95 | -.0008 | .2844 |
| Shift | 160 | 128.15 | 100 | 94 | -.0101 | .2224 |
| Selective | 30 | 20.89 | 0 | 0 | NA | NA |
| Selective | 60 | 42.23 | 100 | 93 | .0037 | .3702 |
| Selective | 100 | 70.84 | 100 | 97 | -.0075 | .3075 |
| Selective | 160 | 112.13 | 100 | 93 | -.0085 | .2410 |

The exact complete-pair population agreement targets are .7000, .4828 and .4856, respectively; the selective scenario's all-invitee target is .4828. The 30-invitation cells produced no available intervals in this screen (30 complete pairs required), so conditional coverage is undefined rather than zero. At other invitation counts all intervals were available and conditional and operational coverage coincide in the observed replicates. The observed 84/100 and 88/100 coverage at 60 invitations motivates further calibration, not selection of a larger N by default. The intervals at 160 invitations still have appreciable widths. These are 1200 stylised synthetic datasets, not participant data. The screen does not use 2000 bootstrap draws or the required 1000 to 2000 datasets per cell. Identical item values within each domain, no item missingness, one positive agreement configuration and a limited shift/selection model restrict inference. Final invitation counts, precision criteria and retest scoring remain unapproved.

## Executed ordinal-item retest precision screen (28 November 2026)

Source HEAD `1194c70e7f8077b0d6e98bccc35ff0847caa54dc`, ordinal driver Git blob `c68bdd80f267c8d908198b3fabbfb7ad2202a965`, verified locally along with the four unchanged source dependencies identified in the preceding screen. Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, single OpenBLAS thread. Command from analysis/: `OPENBLAS_NUM_THREADS=1 python retest_ordinal_calibration.py --reps 100 --boot 199 > ordinal_screen.json` (default seed 20261129). Local JSON SHA-256 `344970082b8b95ec2261c4f4eeb7e169f13ab19db9497a0d38fcffabdb3a2d72`. This is a local execution, not a CI artifact; dependencies differ from the pinned CI runtime.

| Scenario | Invited | Mean eligible pairs | Intervals available / 100 | Covered / 100 | Conditional coverage | Bias | Mean width |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stable | 60 | 47.68 | 100 | 93 | .930 | -.0043 | .4352 |
| Stable | 100 | 79.92 | 100 | 94 | .940 | .0040 | .3468 |
| Stable | 160 | 127.70 | 100 | 95 | .950 | -.0029 | .2772 |
| Shift | 60 | 48.12 | 100 | 96 | .960 | -.0145 | .3792 |
| Shift | 100 | 79.60 | 100 | 95 | .950 | .0035 | .2934 |
| Shift | 160 | 128.16 | 100 | 97 | .970 | -.0026 | .2399 |
| MCAR | 60 | 26.81 | 24 | 21 | .875 | .0228 | .4969 |
| MCAR | 100 | 43.02 | 99 | 87 | .879 | -.0218 | .4698 |
| MCAR | 160 | 69.13 | 100 | 88 | .880 | .0090 | .3640 |
| Selective | 60 | 27.42 | 33 | 30 | .909 | -.0132 | .5212 |
| Selective | 100 | 47.05 | 100 | 92 | .920 | -.0150 | .4547 |
| Selective | 160 | 73.76 | 100 | 93 | .930 | .0064 | .3620 |

Full-data agreement targets are .5698 for stable, MCAR and selective, and .4240 for shift. Complete-pair targets are .5698, .4240, .5531 and .5318, respectively. Analytical eligible-pair probabilities are .8000, .8000, .4349 and .4656. At 60 invitations the MCAR and selective scenarios often fail the 30-pair execution guard; operational coverage (21/100 and 30/100) is therefore substantially lower than conditional coverage (21/24 and 30/33). At 160 invitations the MCAR scenario still covers only 88/100, with mean interval width .3640; increasing invitations alone does not establish nominal coverage. Monte Carlo uncertainty is substantial at 100 replications per cell. Comparisons with the earlier stylised score-level screen are descriptive because the generating distributions and targets differ. These 1200 synthetic datasets do not provide participant evidence or authorize an invitation count. Next evaluate alternative interval constructions on paired datasets with independent confirmation, 2000 bootstrap draws and larger replication counts; prespecify precision and availability criteria before sample-size selection.
