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
