# Rounded sensitivity audit v1.0.0 (27 November 2026)

Run 45990267481, exact source 018081465b81983ae2618afba2d95eb9efb71511, merged via PR 44. All 12 ZIP hashes matched the GitHub metadata and each exact-head.txt matched. Each job passed. Synthetic screening only. P08/P09: 400 bootstrap outer datasets ×199 requested draws =79,600; P09 raw checks: 120 distinct datasets because the same n/effect seed is reused across MAR/MNAR; P03: 16 datasets. No empirical claims.

| Study/N | Mechanism/effect | IPW coverage | Zero-shift coverage | IPW bias (P09) |
|---|---|---:|---:|---:|
| P08 640 | MAR/null | .950 | .950 | not recorded |
| P08 640 | MNAR/null | .500 | .525 | not recorded |
| P08 660 | MAR/null | .975 | .950 | not recorded |
| P08 660 | MNAR/null | .475 | .500 | not recorded |
| P09 440 | MAR/null | 1.000 | 1.000 | .0395 |
| P09 440 | MNAR/null | .300 | .275 | .5007 |
| P09 600 | MAR/null | .775 | .825 | .0310 |
| P09 600 | MNAR/null | .300 | .300 | .4899 |
| P09 600 | MAR/alternative | .925 | .950 | -.0034 |
| P09 600 | MNAR/alternative | .400 | .400 | .4252 |

40/40 intervals returned per cell. P08 heard-only authority null, not full-cohort causal effect: all 160 undefined-outcome gates blocked full-cohort numerical sensitivity. Mean observed at 640/660: 475.98/485.83 MAR; 474.98/486.45 MNAR. P09: stratified blocks, heteroskedastic profile; 31/40 MAR IPW coverage Wilson [.625,.877]. 40/40 is not proof of perfect coverage. New independent-seed higher-precision screening required.

P03: 32 mixed-MAR and 16 outcome-MNAR Rhat diagnostics; >1.01 counts 17/32 and 8/16, >1.05 counts 4/32 and 1/16, maxima 1.10204 and 1.07849. All 16 datasets attained 500. These are selected mean/SD summaries, not global convergence. Compare 30/60 sweeps within the same extended chains; retain original production defaults.

## P08 independent hearing/measurement loss calculation

Balanced groups, hearing loss .05/.10, independent measurement loss .20: X=sum of independent Bin(n/2,.76) and Bin(n/2,.72).

| Assigned N | Expected observed | P(X>=500) |
|---:|---:|---:|
| 640 | 473.6 | .008854 |
| 660 | 488.4 | .162085 |
| 680 | 503.2 | .629306 |
| 700 | 518.0 | .943609 |
| 720 | 532.8 | .997357 |

Calculated locally with SciPy binomial convolution. 720 is an additional candidate, not an approved recruitment target. Does not resolve non-hearing, joint availability, MAR/MNAR or interaction power. Bootstrap screen at 720 plus 60-sweep diagnostics and independent P09 replication configured separately.

Artifact digests and exact source in rounded-sensitivity-artifacts.json. Latest PR validation remains pending.
