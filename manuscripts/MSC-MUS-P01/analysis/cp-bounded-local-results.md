# Local bounded CP results, 27 November 2026

Both supplied JSON files contain synthetic aggregates only. SHA-256 refers to exact uploaded bytes (including encoding). No full independent rerun or empirical observations.

| File | Seed | Scenarios | Datasets | Method evaluations | Failed |
|---|---:|---:|---:|---:|---:|
| cp-bounded-full.json | 20261128 | 360 | 7200000 | 14400000 | 0 |
| cp-extended-full.json | 20261129 | 2376 | 47520000 | 332640000 | 0 |

Original output SHA-256: 6f63557353273064d0ac19bbbd6c4a95510114e83f9687f279ff79b0fb7ebfe8.
Extended output SHA-256: b8bb81c404967097cd523f73b1b294832d6be185133fd44ccfd16a3fc81626a5.

Extended output declares version 1.0.0, complete=true, NumPy 2.3.5, confirmatory_authorized=false. Original script is present at 7aa4925; extension at 8697768. Exact local HEAD and SciPy version were not embedded in supplied output; source association follows the supplied run commands and output schema. Extended grid checked for unique cells, complete accounting, union-null flags and reported MCSE consistency. Raw aggregate files remain local; no participant data or recruitment approval.

The manuscript tables and figure report worst-case MAR joint power over six mean/dispersion settings (not pooled estimates) and maximum union-null rejection per observation mechanism. No-go for approved recruitment. At .30 raw points, first extended-grid N attaining .80 across all MAR settings is 5000; .45 requires 2000, .60 reaches target at 1600; .15 and asymmetric .15/.45 fail at 5000. Under differential MNAR matched, maximum false-positive frequency is 1.0. Pattern-mixture shifts are sensitivity assumptions, not interchangeable estimators to select by observed significance.

Reproduction commands: python cp_bounded.py --reps 20000 --seed 20261128; python cp_bounded_extended.py --reps 20000 --workers 16 --seed 20261129 --output ../results/cp-extended-full.json. Use an unused output path. Record exact HEAD and environment on next execution. No new full run in CI.
