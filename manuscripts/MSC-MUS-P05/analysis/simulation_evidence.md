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
