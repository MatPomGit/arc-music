# P03 imputation calibration audit v1.0.0 (27 November 2026)

CI run 45989294785 at 70556fa3afb62e68889bfb1ae05c008b3554e53f. Five ZIPs downloaded, verified against GitHub SHA-256 and exact-head.txt, and all JSON cells inspected.

| Mechanism | Artifact ID | SHA-256 |
|---|---:|---|
| Complete | 15193256942 | 105aef3f097ef5650d3610a9ea6c2958a128f2035ac62c7ad6136c9e4ca8aaf0 |
| Outcome MAR | 15192618059 | 3eb6b41e6c27a79a41000a316407e2d201d3fc7f3e8af87629af7556d80d671c |
| Predictor MAR | 15192837108 | 3a0fb27ed47bc859ee847ea174eaad7e2d3a5b4a5d88baf9ef934c5ae39d08e4 |
| Mixed MAR | 15193376769 | 41fbd3f1e4006c6ffb202b0b562d279d814ab547e5d1601590de77948e6170b9 |
| Outcome MNAR | 15192957059 | ce0cff9b9ecafe567f4e214f9c98666cdf646bae806c5ef716655db0b8d23d3b |

300 datasets, 30 per mechanism × effect cell; 10 imputations, 5 sweeps. Four analysis methods, no fit failures. Unit tests passed. Full m=50, 15 sweeps smoke job subsequently passed; artifact 15192858267, SHA-256 4ca8fb4c74693fcc9feb2ca3db597a4035736669d68c61ceed1faa91a57af0bd, exact HEAD confirmed. Mixed MAR, 20 datasets, no failures. Null coverage 10/10 for both CC and PMM; alternative coverage and rejection 9/10 for both; Wilson interval for 9/10 [.596,.982]. Smoke only. Screening only: 30 replications imply MCSE up to .0913; rounded reference slopes .000469/.083620 are estimated.

| Alternative | Complete-case coverage | PMM zero-shift coverage | PMM bias | PMM rejection |
|---|---:|---:|---:|---:|
| Complete | .933 | .933 | -.00249 | .967 |
| Outcome MAR | .933 | .933 | -.00160 | .967 |
| Predictor MAR | 1.000 | .967 | -.00397 | .933 |
| Mixed MAR | .900 | .867 | -.00437 | .867 |
| Outcome MNAR | .767 | .767 | -.03383 | .367 |

MNAR near-null PMM rejection .367, coverage .633. Under MNAR alternative, slopes -2/+2 yielded coverage .067/.600; wrong-direction shifts can worsen inference. Not evidence of valid MNAR correction or final MI calibration.

At cap 640 mixed MAR attainment was 20/30 under near-null and 24/30 under alternative. Under the specific DGP, rounded baseline scores 0–10 have mass .05 at endpoints, .10 otherwise. Conditional complete probability is the product of the two independent nonmissing probabilities. Integrating gives p=.7946660955. With iid submissions and no other losses, binomial tail P(X>=500) is .813595 at cap 640, .991001 at 660, .999917 at 680, .9999998 at 700. These are exact planning calculations conditional on the synthetic model; they do not model eligibility or time limits. Candidate cap 660 merits review, not automatic adoption. Code and regression checks reproduce the calculation.

Remaining: more replications at full imputation settings, execution and review of the new trace diagnostics, alternative missing predictor mechanisms and auxiliary-variable calibration; pilot-informed recruitment and scientific review. No empirical data or confirmed final cap.
