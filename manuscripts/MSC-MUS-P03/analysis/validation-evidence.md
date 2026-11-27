# P03 executable validation evidence

Status: PROSPECTIVE; synthetic fixtures only. No human data or independent scientific review.

## Historical local execution (listed blobs only)

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

Imputation sensitivity retains 5 constant deltas, and adds 12 differential deltas: delta + slope*(expression-5)/5, where delta in {-1,0,1}, slope in {-2,-1,1,2}; applied only to missing outcome values, clipped to [0,10], with common imputed datasets and pooled intervals. This is a scenario grid, not a validated correction for MNAR. At that historical snapshot, imputation coverage under repeated sampling, convergence diagnostics, full-text bibliography, psychometric pilot, PDF build, remote CI and independent review remained open. The subsequent CI record below supersedes only the technical execution status.

## Subsequent CI record (PR 70)

Observed GitHub check-run statuses, keyed by exact tested commit; links are evidence of execution, not of scientific calibration. This snapshot precedes the evidence-only commit.

| Tested commit | Validator and Python tests | Manuscript build | Trace smoke | Protocol smoke |
|---|---|---|---|---|
| `286de94` | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079587895/job/140775204306) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079587834/job/140775204559) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079587895/job/140775353217) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079587895/job/140775353221) |
| `4d906df` | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079659840/job/140775439000) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079659819/job/140775438838) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079659840/job/140775602779) | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079659840/job/140775602738) |
| `6911e3b` | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079718901/job/140775633534) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079718932/job/140775633267) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079718901/job/140775756374) | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079718901/job/140775756392) |
| `5612ee2` | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079779860/job/140775834791) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079779863/job/140775834445) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079779860/job/140775953098) | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079779860/job/140775953109) |
| `ce65518` | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079844310/job/140776044775) | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079844281/job/140776044797) | [success](https://github.com/MatPomGit/arc-music/actions/runs/46079844310/job/140776225889) | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079844310/job/140776225879) |
| `0dd8bf8` | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079901606/job/140776234269) | [in_progress](https://github.com/MatPomGit/arc-music/actions/runs/46079901571/job/140776233772) | not reported | not reported |

The tests job executes `python3 validate.py` and Python unittest discovery on the exact PR head. Calibration jobs use 30 replications per cell, 10 imputations and five sweeps; the protocol smoke uses 10 replications per cell, 50 imputations and 15 sweeps. Trace smoke uses four chains and only 20 retained sweeps per chain, so its ESS cannot reach the prespecified 400 threshold. Successful execution is not evidence that the diagnostic screen passed. The numerical artifact contents and rendered PDF have not been independently inspected in this update.

The revised code rejects malformed pooled inference and incomplete traces, retains failed sensitivity scenarios without partial pooling, and preserves threshold diagnostics after failure of the common ordinal fit. The manuscript and survey protocol now describe these safeguards. Higher-precision repeated-sampling calibration, independent reference comparisons, measurement review, prospective approvals and independent review remain open. No fieldwork or confirmatory inference is authorized.
