# P09 calibration audit, 27 November 2026

Scope: author-side technical and scientific self-audit; not independent peer review. Historical artifact inspected: [run 45983137386](https://github.com/MatPomGit/arc-music/actions/runs/45983137386), artifact 15189789939, exact-head.txt = 134951e116ea80a52ac8250ea5be4fb0267cf19d. ZIP contains main.pdf, main.log, power-reproduction.json, calibration-grid.json, missingness-demo.json and calibration-extended.json. Numerical summaries below are derived from JSON, not from workflow success alone. No human observations.

## A01.4: HC3 grid

64 cells × 200 datasets = 12,800 datasets; 38,400 model fits, no failures. Across the 48 hypothesis-cell summaries per mechanism:

| Mechanism | Coverage min/max | Largest absolute bias, points |
|---|---:|---:|
| Complete | .915/.985 | .018846 |
| MCAR | .915/.975 | .027524 |
| MAR | .925/.980 | .028191 |
| MNAR | .210/.975 | .466811 |

MNAR shows severe undercoverage despite numerical success. No universal nominal calibration claim. At coverage .95 and 200 replications, binomial MCSE is about .0154. Inspect the specific adverse cells in the original JSON before selecting a high-precision grid. The generator is synthetic; plausible parameter ranges must be informed by pilot distributions and missingness diagnostics.

## A01.5: repeated-sample bootstrap screen

12 cells, 30 outer datasets each, 99 requested inner draws. Both methods returned intervals for all 360 datasets. Entries are IPW / zero-shift bias in scale points and empirical coverage, rounded.

| H | Mechanism | Effect | Bias IPW / shift | Coverage IPW / shift |
|---|---|---|---:|---:|
| H1 | Complete | null | .007/.007 | .967/.967 |
| H1 | Complete | alternative | -.024/-.024 | 1/1 |
| H1 | MCAR | null | -.044/-.043 | .867/.867 |
| H1 | MCAR | alternative | -.008/-.008 | .900/.900 |
| H1 | MAR | null | -.039/-.043 | .967/1 |
| H1 | MAR | alternative | -.019/-.019 | 1/.967 |
| H1 | MNAR | null | .058/.050 | .867/.867 |
| H1 | MNAR | alternative | .038/.035 | .900/.900 |
| H2 | MAR | alternative | -.007/-.012 | .900/.900 |
| H2 | MNAR | alternative | .038/.019 | .933/.933 |
| H3 | MAR | alternative | -.123/-.124 | .900/.900 |
| H3 | MNAR | alternative | .053/.055 | .933/.933 |

With 30 datasets, coverage increments are 1/30 and MCSE near .95 is about .040. The H3 MAR sample bias is a screening flag, not proof of systematic bias. H3 availability depends on T1 understanding; both baseline endpoints are included in response models. The MNAR figures assess recovery of complete-data truth despite nonidentification. The shift envelope is not a confidence interval. High-precision calibration must use production 999 draws and an adequate outer count (e.g. 1,000 per selected cell, MCSE about .0069 at .95). This proposed design is not yet executed.

## Raw-record stress

Four cells × 200 datasets, three endpoints. Coverage range .925–.980, maximum absolute bias .036. Production preparation masks checked by simulation. Event mismatch and invalid timing do not by themselves imply structural undefinedness.

## Decision and open gates

A01.4: initial grid and raw masks executed; higher-precision calibration and final SESOI/sample-size decision remain open.
A01.5: IPW/bootstrap implementation and screening executed; confirmatory coverage and missingness assumptions not settled. No assertion that IPW solves MNAR.
A01.1–3: literature and validation plans prepared; full-text audit, measurement review and pilot pending.
A01.6: offline allocation/task/manifest contracts implemented after this artifact; no production validation, authorised stimuli, withdrawal policy or recruitment.
A01.7: self-audit only; independent scientific review and latest exact-HEAD PDF visual inspection remain pending. No claim of submission or recruitment readiness.

Reproducibility: preserve the historical artifact link and report scope; no rerunning unchanged cells solely for a fresh report. New CI must verify the new code and manuscript. Source check: Kross & Ayduk (2011) pages 187–191 confirmed via DOI publisher; Qin & Zhang DOI and He DOI resolved; Habermas & Bluck, Belfi et al. and Terwee et al. metadata confirmed. Full-text evidence and APA 7 formatting remain open.

## Targeted follow-up selection (v0.6.2)
Historical grid identifies all eight coverage values below .60 as H1/H2 heteroskedastic MNAR at N=434/588. Worst null N=588: H1 .215 (bias .459566), H2 .210 (bias .466811). Compare matching MAR cells rather than treating larger N as a solution to nonidentification. New independent seeds; 8 HC3 cells × 2,000; H1 null at N=588 under heteroskedastic MAR/MNAR × 1,000 outer × 999 inner draws. Other bootstrap endpoints and alternatives remain lower-precision screening only. No high-precision output yet. Check aggregate exact SHA, all 20 shards, denominators, bias and coverage before further decisions.

## Actual IPW candidate, 999-draw precision screen

Run 46017681854, exact HEAD 0bf50ebaeae35492f5cd7a59847b1b9016396786, seed 20261207. Four cells, 20 independent datasets each, three endpoint models and 999 bootstrap draws per fit: 240/240 available intervals, 239,760/239,760 successful draws. Verified shard indices 0–19 per cell and identical metadata. All tables below are development results; no authorization.

| N / mechanism / effect | H1/H2/H3 coverage | H1 nominal rejection | H2/H3 Holm rejection | True-null family error |
|---|---|---:|---|---:|
| 440 MAR null | .95/.95/.90 | .05 | .00/.05 | .05 |
| 440 MAR distance-only .5 | .95/.90/1.00 | .05 | .05/.30 | .05 |
| 600 MAR null | .90/1.00/1.00 | .10 | .00/.00 | .00 |
| 600 MNAR null | .90/.85/.90 | .10 | .10/.10 | .20 |

H1/H2/H3 bias in raw points: .00080/-.04007/.01280; -.01774/-.06019/-.05399; -.02786/.05275/-.04277; .07490/.10859/-.04366, respectively. True-null FWER 4/20 under MNAR has Wilson interval [.081,.416], MCSE .0894; even 0/20 gives upper limit .161. H3 partial-null Holm rejection 6/20 (Wilson [.145,.518]) cannot establish adequate power. Bias under MNAR and uncertain null error persist; more resampling does not identify missing outcomes. Preserve the historical HC3 and percentile-IPW summaries; this screen uses the actual centered-error candidate. No final N, SESOI or adoption.

| Cell | Artifact ID | ZIP SHA-256 |
|---|---:|---|
| 6 | 15207720315 | 6d7d6f6139dab4234e0712dd2799e923c9f02e22ee83f6dd88a698a889dcd335 |
| 8 | 15206736976 | e54a2eb9be6732dd6dcf50ec1136757af24a42a3fb08f6b259b4ee88cccb7fde |
| 18 | 15207381598 | 9ae1bd3a7214e7f4f73fde46f895cc233f129492247acbdb1a483e392e733b27 |
| 21 | 15207406827 | 45ab0304a9958a3fa91de4f5efa06d5acb28fa30d321cc299c92b6f570bff23d |

Actual centered-bootstrap IPW candidate: see [candidate-precision-evidence.md](candidate-precision-evidence.md). This is separate from historical HC3 and percentile-bootstrap results; confirmation is not authorized.
