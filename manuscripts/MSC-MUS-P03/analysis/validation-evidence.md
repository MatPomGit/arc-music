# P03 executable validation evidence

Status: PROSPECTIVE; synthetic fixtures only. No human data or independent scientific review.

Local execution used Python, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, statsmodels 0.14.6 and single-thread OpenBLAS. The following Git blobs match the locally executed source and test files byte-for-byte, verified against GitHub after upload:

- `power.py`: `cc196a2208c6a1261405e8c1fa6e5379c652ebbe`
- `stress.py`: `efe2267cee07ab8dded75421f1a9eda8412b53c5`
- `models.py`: `ea46a4891cd53488ef6d23792c356edb916a2e3b`
- `imputation.py`: `090dbe9cd840b48a4007b80bef7add7eb3332340`
- `test_analysis.py`: `fa80c21a8b63edca02c56000847a6391fac1aed9`
- `test_imputation.py`: `8509ab95d1773ca31124fba79a98790e6bae12b4`
- `robustness.py`: `a16ade7655e79813b5d5f6070aa76d20f10fd38a`
- `test_robustness.py`: `d05f366623905b7025f501ea4a19b94214613ca4`

Command: `OPENBLAS_NUM_THREADS=1 python -m unittest -v`

Result: 20 tests passed, 3.248 s (6 complete-record, 3 power, 6 imputation, 5 robustness). All existing synthetic tests passed; the added tests cover differential delta integrity, natural spline linear tails, pointwise contrasts, ordinal count regression, rejection of noninteger outcomes in ordinal models, and diagnostic/recency checks. The new stress script was executed separately for 24,000 trials; base power.py for 16,000 trials. See stress-report.md.

Robustness CLI: `python robustness.py synthetic.csv --data-kind synthetic --out robustness-results.json`. H1 natural cubic spline at fixed knots 0,3,7,10 with pointwise (not simultaneous) contrasts relative to score 5. H1–H4 proportional-odds logit sensitivity with HC0 sandwich intervals when outcomes are integer and at least two levels observed. Proportional odds is an assumption and has not been validated; ordinal estimates have different estimands. VIF and aggregate influence/residual summaries do not trigger deletion. H1 recency sensitivity restricts to episodes <=7 days.

Imputation sensitivity retains 5 constant deltas, and adds 12 differential deltas: delta + slope*(expression-5)/5, where delta in {-1,0,1}, slope in {-2,-1,1,2}; applied only to missing outcome values, clipped to [0,10], with common imputed datasets and pooled intervals. This is a scenario grid, not a validated correction for MNAR. Imputation coverage under repeated sampling, convergence diagnostics, full-text bibliography, psychometric pilot, PDF build, remote CI and independent review remain open.
