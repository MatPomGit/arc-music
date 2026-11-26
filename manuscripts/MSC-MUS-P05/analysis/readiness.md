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

## v0.8.0 implementation

CI 45894003009 on d4209e2 passed unit tests at inspection; simulations and PDF were still in progress. Added common-metric baseline/target discrepancy diagnostics, trace correction explicitly distinguished from validated robust CFI/TLI/RMSEA, rank/folded split R-hat, approximate ESS and seven regression tests. Paired synthetic calibration configured for 90 datasets. Full sample-size calibration, reference software comparison, RMSEA interval, joint FCS convergence, validity contrasts and scientific review remain outstanding. No participant results.

## v0.9.0 implementation

Added all six external validity contrast slots, multiplicity handling, five regression tests, synthetic null/alternative validity calibration and sample-size decision protocol. The CI smoke configuration is 300 datasets; results pending. Both prior runs were in progress with unit tests passing. The numerical sample-size decision, large calibration, reference-estimator comparison, full-text audit and independent scientific review remain open. No participant results.

## v0.10.0 implementation

CI 45894003009 passed at d4209e2. CI 45894330847 on 9daea1e failed one of 47 unit tests: with 99 bootstrap draws the smallest Holm-adjusted p is .06 for six slots. Test now checks both 99-draw nonrejection and 199-draw rejection, with no change to the estimator, alpha or family. Added two independent-formulation polychoric numerical tests, partial bibliographic claim/metadata audit, corrected ERP-IA-6 context and explicit manuscript development gates. CI 45894186937 still running at initial inspection. Full estimator reference, larger sample-size calibration, complete source audit and independent review remain open.

## v0.11.0 implementation

CI 45894529075 passed all unit tests and simulations through invariance at inspection; later steps pending. Downloaded and SHA-256 verified artifact 15152208946 from completed CI 45894186937 (b3590c4); all seven JSON files inspected. Evidence and adverse outcomes recorded in simulation_evidence.md and manuscript. Eight-item first factor correlation coverage was 23/30; weak/high-correlation 35-item conditional CFA yielded 0/8 proper fits. No N selected. Added 60-scenario sharded CFA calibration driver, deterministic seeds, strict aggregation and four unit tests. Large calibration is not automatically launched; reference validation and broader EFA/MI/validity calibration remain open.

## v0.12.0 implementation

Both previous CI runs passed unit tests at inspection and remained in progress. Added selected-count EFA recovery, four factor-count smoke datasets including two with protocol 500 permutations, paired Wald/Fisher-delta/percentile/basic interval comparison, and five regression tests. New results pending. No claim of repaired coverage, increased power, full-pool protocol recovery or selected N. Invariance power, reference estimator, large calibration and scientific review remain open.
