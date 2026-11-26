# Readiness register (v0.1.0)

- Construct, episode anchor, 35 candidate items, provisional hypotheses and staged study protocol: drafted.
- Bibliography: DOI/title checked against accessible records; full-text claim audit, complete bibliographic fields and search update outstanding.
- P02 qualitative traceability: pending actual qualitative data, not inferred from protocol.
- Comparator Polish forms, suitability and licences: pending. PAQ-S-PL is available within the broader project, not automatically required here.
- Ethics, consent, preregistration and independent review: pending.
- Ordinal analysis implementation, recovery simulations, EFA/CFA sample-size decision and calibration: pending.
- Empirical results, norms and clinical cutoffs: none.

Assessment is the existing target; its assessment science focus and registered-report route warrant an editorial scope check for a nonclinical instrument. Psychology of Music remains the alternative. Verify current publication conditions before submission.

## v0.2.0 implementation

The previous CI passed repository validation and initial unit tests but failed LaTeX because lmodern.sty was absent. The workflow now installs lmodern explicitly. Development ordinal EFA and synthetic recovery code are implemented; independent numerical checks, CI results and full-pool calibration remain pending. Robust ordinal CFA remains unimplemented. No participant data or simulated results are asserted before execution.

## v0.3.0 implementation

CI 45892064058: all steps passed, including repository validation, unit tests, development simulation and PDF build. Artifact metadata confirmed exact HEAD f2be72f54c6f9da37e5117b01f844660ad80cc14. New conditional-weight ordinal CFA, participant-bootstrap interface and two reliability estimands are implemented. Full 35-item synthetic smoke scenarios are wired into CI. New results remain pending. Robust WLSMV, confidence-interval coverage, independent comparison, empirical content validation and permissions remain open.

## v0.4.0 implementation

CI 45892825483 passed on 493f27f1bef363ed37673dfb9c24e647c6daf6c6, including 35-item conditional-weight simulations and PDF compilation. New empirical influence-function DWLS with threshold uncertainty, sandwich covariance and a moment-matched residual test is implemented. Regression tests cover the analytic model Jacobian, leave-one-out influence checks, proper fits and missing-data rejection. New CI runs a small calibration with explicit failures and Monte Carlo uncertainty. Independent WLSMV reference, robust fit indices, larger coverage studies, measurement invariance, MAR/MNAR and scientific review remain outstanding. No empirical participant results.

## v0.5.0 implementation

CI 45893153993 at 002c0a6 passed validator and unit tests at time of inspection; final result pending. New MAR complete-record IPW, MNAR exponential tilt, weighted ordinal moments, bootstrap interface and synthetic comparison implemented. Five tests added. The planned item-level multiple imputation, full sample-size calibration, reference estimator comparison, robust fit indices and invariance remain outstanding. New CI results pending.

## v0.6.0 implementation

CI 45893153993 passed at 002c0a6. CI 45893355394 on ca681f8 still in progress at inspection. New affine-linked ordinal group diagnostics with joint influence covariance, four regression tests and 120 synthetic two-group datasets are implemented. They do not constitute an independent validation of ordinal invariance. Final nested multi-group model, reference comparison, robust CFI/TLI/RMSEA, item-level MI and sample-size/coverage calibration remain open. No latent mean comparisons or participant results authorized.

## v0.7.0 implementation

CI 45893710926 at becaf6e passed computational steps when checked; final PDF status pending. Added ordinal probit FCS, independent chains, delta sensitivity, Rubin parameter pooling, strict failure accounting, six unit tests and 24 synthetic datasets for smoke calibration. Convergence, congeniality, coverage and full-pool MI remain unverified. Robust fit indices, independent reference estimator, final sample-size calibration and scientific review remain open.
