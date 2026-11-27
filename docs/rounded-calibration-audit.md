# Exact-HEAD calibration audit (27 November 2026)

Run 45988878791, source commit dbb0f175e4624dbaf63f24bb61c35f893a419aaf. The two completed ZIPs were downloaded, SHA-256 verified against GitHub metadata, and exact-head.txt and JSON inspected.

| Artifact | ID | SHA-256 |
|---|---:|---|
| P01 | 15191799855 | 606dcaa628d034e98dfef8b2ce9c916a08f91c7146f0bc1380163df339cf3b63 |
| P03 | 15193146592 | 6532ce62c954a51a8bf0cdadf3a9a0b2191deb150cb7d77c30357848e802e85b |

P01 reproduced 200,000 Gaussian summary simulations exactly: alternative rejection .80578 (MCSE .00125), null rejection .05084; coverage .94982/.94916.

P03 executed 24 primary and 36 stress cells, 1,000 replications per cell. Primary MAR target attainment at cap 560 was .403–.414; at cap 580 .972–.981; at cap 640 1.000 in all four MAR cells. The primary alternative rejection across all caps and mechanisms was .900–.926. This is a bounded continuous linear model, not empirical evidence.

| Cap | Rounded alternative, outcome MNAR: attainment | Bias | Coverage | Rejection of zero |
|---:|---:|---:|---:|---:|
| 560 | .000 | -.03954 | .697 | .383 |
| 600 | .307 | -.03764 | .687 | .409 |
| 640 | .993 | -.03560 | .720 | .466 |

At cap 640 the rounded near-null MNAR rejection rate was .277, coverage .734. Attainment .993 has Monte Carlo SE .00264; coverage .720 has SE .0142. Higher cap does not restore calibrated inference. The rounded reference projection is estimated rather than exactly zero. The eight-week limit, ineligible submissions and empirical attrition are not modeled.

P08 and P09 rounded calibration jobs were still running at inspection. No final recruitment decisions, independent review or empirical validity claims. Historical local reproductions remain separate.

## P03 follow-up

A new calibration script uses the existing production prepare, fit, draw_imputations, shift_outcome and pool functions. It retains partial submissions until 500 complete records or cap 640, and reports conditional and operational coverage, failure rates, bias, RMSE and rejection. Five mechanisms, rounded null and alternative, 30 replicates per cell at m=10 and five sweeps; separate 20-dataset smoke run at the full m=50, 15 sweeps. Candidate cap 640 is not approved. The selected differential shifts are diagnostics, not identified MNAR corrections. Reference targets use independent 500,000-row samples; nonzero reference uncertainty and optional auxiliary predictors require further study. The small runs cannot establish coverage or chain convergence. CI pending.
