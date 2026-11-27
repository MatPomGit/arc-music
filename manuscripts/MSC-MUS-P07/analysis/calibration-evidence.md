# P07 calibration evidence v0.3.0

CI 45899777729, calibration-screen job 140182433032, exact source HEAD 9e51be6c577869c506f9635bd6b6e2b9f00c6c0c. The job completed successfully and emitted the complete JSON preserved in calibration-results-v0.3.0.json. 44 cells x 200 replications = 8800, no failures. This is a preliminary synthetic screen, not empirical evidence.

Under 30% expected stage loss and MAR with latent beta .4, rejection rates at 10/25/40% creation prevalence were 46/79.5/92% (N=80), 83.5/99/100% (N=160) and 99/100/100% (N=320). For N=160 with 10% creation, mean switcher count 88.3; at 25%, 132.38. Finite 100% rejection does not establish certainty. Null reference slopes are small but not exactly zero; rejection-zero ranges 3–6.5% in core null cells. At 200 replications Monte Carlo uncertainty is substantial.

In the confounded scenario with latent beta 0, reference associational slope .411694 and rejection-zero .985; an association is not a causal effect. No final recruitment target. Creation prevalence, ongoing exclusion, attrition and time-varying confounding need pilot-informed stress calibration. Exact-head results archived from logs, not independently reproduced.

## Exact-head reproduction

Run 46010489946, head f2c377ec0565610fe85578aa57f131349ef9ad2e: downloaded and checked all three archives. Artifact 15203936780 SHA-256 ef9450d654e91e307f659229aac3672066592007c5f8562aaecf65386770e7a7: 44×200, 8,800 valid, zero failed; N160, MAR, .4 latent contrast and 10/25% creation prevalence, rejection .835/.990, coverage .960/.975, mean switchers 88.3/132.38. Artifact 15204036765 SHA-256 f4f7dcb8f30cdd0c239fffafa527d213fe0231e2c861bba01a4d776977bf2947: N160, 12×1000, all valid. Artifact 15203786986 SHA-256 3e2b306265cff3e6d1f4d893673e6c8dbdd37934a4919643b3379fb48f9a4800: N320, 12×1000, all valid. At .45 final-day withdrawal, .4 latent contrast, .05/.10 prevalence, rejection .614/.887, reference coverage .958/.944, mean switchers 76.573/124.974. Total 32,800 successful historical H1 fits, not a causal contrast, final N or proof of coverage under other missingness. The later H2/H3 candidate screen is distinct.
