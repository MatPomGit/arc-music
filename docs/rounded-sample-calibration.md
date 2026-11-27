# Rounded sample calibration v1.0.0 (27 November 2026)

Independent local reproduction from HEAD 86f432e (not exact production execution). Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0. All data synthetic. Seeds 20261127 (P01/P03 and separately P08/P09), 20261129 (P03 stress), 20261128/20261201 (recruitment).

| Study | Proposed N | Analytical power | Local screen |
|---|---|---:|---|
| P01 | 420 randomised, 15% loss | .80689 | 100,000 datasets each null/alternative; rejection .05084/.80578; MCSE .00069/.00125 |
| P03 | 500 complete | .91550 | 8,000 continuous and 12,000 stress datasets; primary alternative rejection .903–.921 |
| P08 | 500 complete | .91738 | 7,000 datasets; complete alternative H1 .900, Holm H3 .624 |
| P09 | 440/600 randomised, 20% loss | .90563/.90654 | 9,600 datasets; 64 cells × 150; preliminary |

P01 factorial matching contrast d=.30, 105 per cell. P03 partial r=.15, ten nuisance degrees of freedom. P08 marginal d=.30; simulation alternatives .45/.60 raw points. P09 d=.35/.30; simulation alternative .5 raw points, not necessarily equal to SESOI.

## Recruitment sensitivity (50,000 P03 datasets)

| P03 cap | Primary MAR attainment | Rounded predictor-MAR | Rounded MNAR |
|---|---:|---:|---:|
| 560 | .4028–.4146 | not evaluated | not evaluated |
| 580 | .9782–.9788 | .435 | .009 |
| 600 | 1.000 in both screens | .9735 | .295 |
| 620 | not evaluated | 1.000 | .903 |
| 640 | not evaluated | 1.000 | .996 |
| 660 | not evaluated | 1.000 | 1.000 |

Primary MAR: 5,000 per cell; stress: 2,000 per cell. Observed 1.000 does not guarantee attainment; eight-week cap and other losses not modelled. At cap 560, rounded MNAR alternative rejection .413, coverage .703, bias −.0378. Consider cap 640; current 560 remains unchanged pending approval.

P08: at 20% independent loss, expected 512/528 outcomes with 640/660 randomised; exact probability of at least 500 observed for one endpoint .89074/.99668. Not joint endpoint availability. With N640 H1 MCAR/MAR alternative rejection .922/.926; Holm H3 .606/.550. MNAR H1 global-null rejection .596 and alternative coverage .376. Hearing gate and bootstrap not calibrated.

P09: MAR H1 alternative rejection .700–.973 at 440, .800–.993 at 600; minimum MNAR pointwise coverage across endpoints .313/.247. Maximum absolute MNAR bias .477/.451 points. Low replications: screening only. No causal/empirical claims. Do not equate MNAR rejection with valid power.

Total 286,600 simulated datasets/replicates excluding reference samples and duplicate reruns. Local independent reproduction archive SHA-256 c26c190857def3313318c64bd0050e2bf5d86225de380e0143d9eec652ff4bfe. Full numerical JSON, local scripts and environment are provided in the accompanying archive. Exact production calibration configured separately; final CI and scientific review remain open. No N approved by these results.
