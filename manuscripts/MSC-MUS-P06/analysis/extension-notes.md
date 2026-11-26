# Analysis extension v0.3.0

- Bounded simulation estimates the observed-scale target from a large independent synthetic reference per latent slope; report its Monte Carlo SE. This is not exact truth. Fixed six-session and 30% missingness design is a calibration slice, not final power.
- Observation model uses pre-session covariates and day with ridge-regularized logistic slopes; report positivity and compare caps 10/20. Weight uncertainty is propagated by participant bootstrap with re-estimation.
- Pattern-mean shifts cross five additive shifts and three differential shifts by within-person avoidance. Imputed conditional means are bounded; deterministic mean sensitivity is not Rubin multiple imputation. Bootstrap replicates the whole algorithm. No inference for creators without observed outcomes in this sensitivity target.
- Input to sensitivity is a prevalidated session ledger with complete predictors and post timestamps, including missing/out-of-window outcomes; automatic construction of that ledger from raw logs remains a gate.
- Secondary tests are three predeclared coefficients; Holm adjustment across all three. Interaction uses centered avoidance and relief; reports association, not mediation.
- The previous CI failed because publication.md exceeded 500 characters. It was shortened without changing repository validation. Remaining gates: full calibration, missing-ledger implementation, ethics, instruments, bibliography and independent review.

Update v0.4.0: the raw-session ledger now enforces the timing rules and preserves missing follow-ups. Primary observations are not conditioned on post-response completion. The session-ledger CLI is implemented. Recruitment/consent, activity identifiers across follow-ups, independent daily check-ins and field data capture are still separate implementation gates.

Version 0.10.0 supersedes earlier follow-up timing and activity-identity descriptions. The primary window is 24–28 h from session end, with 24–26 h sensitivity. Opaque identifiers must match; unknown relevance and cancelled activities remain missing outcomes.
