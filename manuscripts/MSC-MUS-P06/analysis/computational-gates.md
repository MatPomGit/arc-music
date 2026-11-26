# Computational stage v0.2.0

- Primary implementation: within transformation, complete-case selection, cluster CR1 sandwich with participant degrees of freedom, two-sided t intervals. CR1 is provisional until null calibration. Timing: follow-up 24–28 hours after post-session assessment; pre-session timestamp must precede post-session timestamp. No actual session end timestamp exists yet; the diary needs an explicit start/end event to verify the 15-minute post window.
- Synthetic generator: participant intercepts and random slopes, AR(1) errors, MCAR/MAR/MNAR outcome loss calibrated in expectation. Continuous generated outcomes preserve the known slope; bounded/ordinal outcome calibration, dropout and selective reporting are still necessary. MNAR bias is not corrected by complete-case analysis.
- Smoke grid is CI only, not a basis for a final sample size. Full factorial run is deliberately separate; use at least 1000 replicates per retained design cell.
- Missing-data sensitivity models, secondary tests, bounded outcomes and diary collection interface remain unimplemented.
- Bibliographic metadata and full texts need independent verification; the prior measurement-gates claim of DOI checks was premature. Do not treat those six references as audited.
- CI includes tests, synthetic smoke results, manuscript compilation, and exact HEAD evidence. No empirical results.

Version 0.10.0 supersedes earlier follow-up timing and activity-identity descriptions. The primary window is 24–28 h from session end, with 24–26 h sensitivity. Opaque identifiers must match; unknown relevance and cancelled activities remain missing outcomes.
