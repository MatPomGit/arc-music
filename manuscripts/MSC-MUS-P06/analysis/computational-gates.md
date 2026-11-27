# Computational readiness gates

Status: prospective. The current analysis contract is [README.md](README.md); the historical numerical evidence and its verification scope are recorded in [reproduction-status.md](reproduction-status.md).

| Area | Implementation and remaining gate |
|---|---|
| Primary model | Within-person fixed effects and participant-cluster CR1 inference are implemented. Inferential calibration remains provisional. |
| Session ledger | Actual start/end events, pre/post windows, matched activity tokens and endpoint states are implemented in ledger.py. The current timing rules are defined in README.md. |
| Missingness and secondary models | sensitivity.py and secondary.py implement candidate IPW, bounded conditional-mean shifts, participant bootstrap and fixed-family Holm reporting. Full-session sensitivity is withheld when applicability is undefined or unknown. |
| Denominators and import | daily.py, export_schema.py and withdrawal_audit.py implement candidate enrollment/check-in and cessation checks. They do not authorize collection or retention. |
| Simulation | Continuous, bounded, cluster, missingness and stress simulations exist. Historical table reproduction is limited to the recorded HEAD and fields; full bootstrap coverage and final sample-size calibration remain open. |
| Field collection | No approved diary application, validated state indicators or participant data. |
| Literature | See bibliography-audit.md for the scope of metadata and selected-claim checks; full-text review remains incomplete. |
| Validation | Dedicated CI tests, synthetic smoke runs and LaTeX compilation are configured; current-HEAD success must be verified separately. |

No empirical outcomes, independent scientific validation, ethics clearance or final recruitment target are implied by implementation or a successful CI run.
