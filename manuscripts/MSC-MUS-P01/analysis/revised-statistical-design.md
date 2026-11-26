# Revised statistical design H6 and H10 (26 November 2026)

This is a prospective synthetic design decision, not an empirical finding. Baseline: cee6e03, extended Monte Carlo showed H6 MNAR type-I inflation and H10 low power and covariance boundary fits. The primary models are changed, not the hypotheses.

## H6
Working-independence marginal linear model with the same within/between-person covariates and contrast, CR2 participant-cluster covariance and contrast-specific Satterthwaite degrees of freedom. Point estimate is OLS, not GLS. Pilot 2,000 replicates/cell, N=80/K=8, seed 20261126, 95% CI: null rejection complete .0535, MAR .0600, MNAR .1020. Prespecify conservative two-sided alpha .04 (96% interval) for H6; tested on independent seed 20261201, 2,000 replicates/cell:

| Mechanism | Null rejection | Coverage | Bias | Power at -.25 | Mean df |
|---|---:|---:|---:|---:|---:|
| Complete | .0375 | .9625 | .001361 | .9255 | 60.72 |
| MAR | .0370 | .9630 | -.003907 | .8995 | 57.27 |
| MNAR | .0670 | .9330 | -.045506 | .9640 | 56.49 |

The independent validation seed is not used to select the alpha. These are local results (Python/NumPy 2.3.5/SciPy 1.17.0); same DGP and formulas in revised_design.py; exact-HEAD CI reproduction pending. The MAR calibration is conservative for this DGP, not a universal proof. MNAR violates identification; no frequentist calibration under unrestricted MNAR is possible. Report fixed-delta pattern mixture with participant bootstrap and consider the result inconclusive if direction or threshold changes across a prospectively justified range. No adjustment of alpha based on the observed study result. The mixed model remains a sensitivity estimator. Actual design-specific recalibration is required once pilot-derived nuisance parameters and missingness mechanisms are specified.

## H10
Randomize fixed-version tools, balanced allocation. Define primary estimand as the difference of mean first-to-last assigned-task enjoyment changes, not a mediator effect. Invite all randomized participants to the final standardized session independently of intermediate attendance; actively collect first and final ratings without excluding nonadherent participants. Missing endpoint ratings remain missing, not zero; record engagement and reasons. First-session enjoyment is post-assignment, so standardize within arms to each arm's own distribution, never treat it as a pretreatment common baseline. Primary estimator is arm-specific linear outcome regression for change on first-session enjoyment, standardized over all assigned first ratings; use influence-function variance including fitted regression and empirical first-rating distribution. Assumes complete first rating, correct conditional mean and MAR given first rating/arm; prospectively include observed history and prespecified covariates if needed. If first rating is missing use prespecified joint imputation/sensitivity protocol, not complete-case exclusion. Fixed arm-specific delta shifts of missing final ratings are sensitivity, not identifiable effects. Marginal repeated-session trends, novelty ratings and regulation remain secondary; no causal novelty mediation.

Local simulation, 2,000 per cell, N=600/800/1000, K=8, nominal recovery probability .85 (actual MAR ~.834), effect -.35 native outcome units, independent seeds 20261127+N:

| N | Missing | Null rejection | Power | Coverage at effect | Actual endpoint retention |
|---:|---|---:|---:|---:|---:|
| 600 | Complete | .0565 | .7935 | .9435 | 1 |
| 600 | MAR | .0445 | .7300 | .9555 | .8341 |
| 600 | MNAR | .0660 | .5775 | .9340 | .8177 |
| 800 | Complete | .0505 | .9160 | .9495 | 1 |
| 800 | MAR | .0550 | .8680 | .9450 | .8344 |
| 800 | MNAR | .0715 | .7235 | .9285 | .8176 |
| 1000 | Complete | .0470 | .9605 | .9530 | 1 |
| 1000 | MAR | .0480 | .9215 | .9520 | .8335 |
| 1000 | MNAR | .0830 | .8075 | .9170 | .8170 |

Choose N=800 randomized (400/arm) as an illustrative minimum of tested sizes for >=80% power under the improved MAR recovery design; power Wilson 95% MC interval approximately [.852,.882], null .055, coverage .945. N=1000 is a conservative planning alternative. Neither is a recruitment authorisation or empirically justified sample size. If resources do not permit N or endpoint recovery, H10 remains exploratory; do not lower power target. The MNAR power cannot support a confirmatory claim. Simulate plausible retention, first-rating missingness, covariance and smallest meaningful effect after pilot; if outcome model fails, evaluate augmented IPW or joint imputation before lock.

New smoke tests check CR2 against HC2 oracle, hidden-outcome invariance, complete-data endpoint estimator and exact delta shift. Full reproducibility script generates Wilson MC intervals and bias MCSE. Current exact-HEAD build and independent review remain required.
