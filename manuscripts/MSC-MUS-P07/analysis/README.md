# P07 analysis contract v0.2.0

PROSPECTIVE. Research owner: Mateusz Pomianek; authorship determined by actual contribution. No participant data. The unit is a prescheduled window, not a creation session. Retain all scheduled windows. The initial estimate uses complete observed switchers, not causal inference. No comparison of creation vs non-creation across different people as the primary model.

Run python -m unittest -v in this directory after installing requirements.txt. Run python inference.py windows.csv on a frozen authorized export, never in CI with participant data. The code implements H1–H3, outcome-specific complete switcher sets, Holm correction with a fixed two-hypothesis secondary family, common complete-subset models and a narrower timing sensitivity. Timestamp schedule generation, field capture, enrollment denominators beyond the flat window ledger, missingness sensitivity, full power calibration and pilot measurement checks remain open. No field application, ethics approval or enrollment.

Power design: vary participant propensities and serial dependence, outcome-dependent exposure, floor/ceiling, informative missingness. Calculate probability of usable within-person contrasts, power under the observed-scale target and coverage. Do not interpret the count of windows as independent observations. Distinguish exposure missingness from outcome missingness.

Bibliography: targeted DOI-backed metadata search on 2026-11-26; sources on listening are indirect, Huang et al. directly concern creation but not affect outcomes. Full-text audit and current journal conditions pending. The 21-day schedule and single-item ratings are provisional.

Narrow timing comparison uses baseline 0–5, exposure/first outcome 60–65 and late outcome 180–185 minutes. H2 does not require the H1 response; H3 requires initial desired arousal and first-hour actual arousal, not valence60. An unavailable secondary model does not reduce the planned Holm family. Common-subset comparisons are descriptive. No raw identifiers are included in output; report counts, not identities.
