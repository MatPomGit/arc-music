# P03 stress calibration v0.2.0

Status: PROSPECTIVE. All values are synthetic. No human data.

## Reproduction evidence
The original power.py was reconstructed locally and Git blob identity verified: cc196a2208c6a1261405e8c1fa6e5379c652ebbe. Executed with seed 1729 and 2,000 replicates per scenario; all eight reported rejection and coverage rates reproduced exactly. The new stress.py was executed locally with seed 2718, 2,000 replicates per scenario; the GitHub blob efe2267cee07ab8dded75421f1a9eda8412b53c5 matches the executed file. NumPy 2.3.5, SciPy 1.17.0, single-threaded OpenBLAS.

Commands:
```sh
OPENBLAS_NUM_THREADS=1 python power.py --seed 1729 --reps 2000 --out power-results.json
OPENBLAS_NUM_THREADS=1 python stress.py --seed 2718 --reps 2000 --out stress-results.json
```

## Scenario definition
Latent motive dependence rho=.6; initial continuous-DGP partial correlation 0 or .15; continuous versus rounded 0–10 responses. The full-data projection for rounded data is approximated using an independent 500,000-row reference. The predictor-MAR scenario removes expression scores with probability logistic(-1.9+.20*(y-5)+.1*(pre-5)), conditional on observed post/pre clarity. The MNAR interaction scenario removes outcome scores with probability logistic(-1.9+.25*(5-y)+.15*(expression-5)*(y-5)). For complete-record regression, both mechanisms are implemented as exclusion masks, not imputed datasets. This stress test does not validate MI. Target 480 complete, cap 560 submissions; eight-week stopping limit not simulated. Rejection tests the zero coefficient; coverage targets the pre-selection projection. Discrete null target is near zero but estimated with simulation error.

| r in continuous DGP | rounded | mechanism | projection target | mean complete n | fraction n=480 | bias | coverage | rejection |
|---:|:---:|---|---:|---:|---:|---:|---:|---:|
| 0 | no | complete | 0 | 480 | 1 | -.000284 | .948 | .052 |
| 0 | no | MAR-predictor | 0 | 477.341 | .580 | .000460 | .9465 | .0535 |
| 0 | no | MNAR-interaction | 0 | 470.010 | .151 | -.031243 | .776 | .224 |
| 0 | yes | complete | -.000499 | 480 | 1 | .000907 | .9465 | .0545 |
| 0 | yes | MAR-predictor | -.000499 | 477.344 | .593 | .000537 | .9505 | .049 |
| 0 | yes | MNAR-interaction | -.000499 | 469.429 | .137 | -.032943 | .7695 | .240 |
| .15 | no | complete | .083414 | 480 | 1 | -.000213 | .951 | .8975 |
| .15 | no | MAR-predictor | .083414 | 477.512 | .6135 | -.000339 | .952 | .906 |
| .15 | no | MNAR-interaction | .083414 | 462.437 | .027 | -.036750 | .706 | .439 |
| .15 | yes | complete | .083303 | 480 | 1 | -.000059 | .9545 | .8865 |
| .15 | yes | MAR-predictor | .083303 | 477.284 | .578 | .000315 | .952 | .904 |
| .15 | yes | MNAR-interaction | .083303 | 461.776 | .029 | -.038508 | .690 | .3965 |

## Interpretation
The rounded complete scenario yields 88.65% rejection at the alternative, so 90% power is not guaranteed. The MAR predictor scenario attains the complete-record target in only 57.8–61.35% of alternative simulations. MNAR leads to substantial selection bias and poor interval coverage; HC3 cannot correct bias. The approximate null rejection reaches 24% under rounded MNAR. Neither increasing the sample alone nor selecting favourable scenarios solves this. Existing planning target and cap remain provisional until feasibility, pilot and MI calibration. The constant delta shift already implemented for missing outcomes may not capture interaction-dependent selection; include a differential delta indexed by expression motive before freeze.

## Open gates
Run existing model/imputation regression suite at exact HEAD; validate MI coverage and interaction-sensitive delta scenarios, ordinal and nonlinear models, and external review. No claims of causal or clinical benefit.
