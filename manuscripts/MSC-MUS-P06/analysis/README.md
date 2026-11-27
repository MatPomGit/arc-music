# P06 prospective analysis contract

Version 0.13.0. No participant data. Owner: Mateusz Pomianek.

The primary target is the within-person slope of pre-session avoidance on interference with a predeclared valued activity at 24 h, adjusted for pre-session distress, expected difficulty and study day. First eligible session per local day; eligibility determined before exposure outcome. Restrict primary complete-case analysis to timestamp-valid sessions with at least two observations per person. Do not select sessions according to relief or completed activity.

Pilot: 15–25 volunteers for feasibility only, excluded from confirmation. Assess burden, comprehension, score range, repeatability of reporting, missingness and within-person variation. Candidate thresholds (not yet locked): at least 70% valid follow-ups, median at least four eligible sessions, no severe floor/ceiling concentration; revise and document before confirmatory enrollment.

Power calibration: simulate 80/120/160/240 creators, 4/6/10 eligible sessions, 15/30/45% dropout or missingness, varying within-person exposure variance, residual SD, serial correlation and participant slope heterogeneity. Explore slopes 0, 0.15, 0.30, 0.45 outcome points per exposure point. The smallest effect of interest needs substantive justification in the pilot; no claimed sample target yet. Assess type-I error, coverage, bias, power and Monte Carlo uncertainty. Target at least 1000 replicates per retained design cell. Recalibrate under informative missingness.

Primary endpoint and hypotheses must be preregistered. Secondary relief and brooding analyses are separate from P01 H6; avoid duplicate confirmatory reporting. Use Python; no R dependency. Diary items are proposed operational indicators, not validated scales. No scale items or copyrighted lyrics are included.

Remaining gates: measurement permissions and Polish validation, ethics, diary implementation, simulation and calibrated inference, missingness sensitivity, full-text literature audit, PDF compilation and independent review.

## Executable ledger
Run `python analyze.py session-log.csv --data-kind synthetic --bootstrap 499` after data lock. The raw log contains session start and end events, pre/post/follow-up responses and prospectively assigned eligibility. Pre assessment is 0–15 minutes before start; post assessment 0–15 minutes after end; follow-up 24–28 hours after end. Missing post responses do not exclude an otherwise eligible primary observation. Invalid or missing follow-up is retained as a missing outcome in the sensitivity ledger. Report exclusion counts; no imputation of non-creation days. Enrollment and evening check-in denominators are implemented as separate input files. Use only synthetic data for CI.

Activity tokens must match and relevance must be confirmed. A missing, mismatched or no-longer-applicable activity produces missing interference. The outcome refers to the first fixed 24 hours; early follow-ups are invalid, not shorter versions of the primary outcome. Prespecified alternative window 24–26 hours. No raw text activity labels are exported.

## Denominator analysis
Run `python analyze.py session-log.csv --data-kind empirical --enrollment enrollment.csv --checkins checkins.csv --bootstrap 499`. See daily-data-dictionary.csv. Enrollment specifies a 14-day calendar and optional effective withdrawal date (first date with no further collection). Evening check-in asks for all naturally initiated AI music sessions that local day, including unlogged sessions. A missing count or check-in is unknown, never zero. Counts conflicting with logged starts are flagged; report separately. The positive count discrepancy is a lower bound of unlogged sessions, not an outcome imputation. No raw text is collected. Window sensitivity compares the same prespecified model at 24–26 h against 24–28 h. The narrow-window estimate can be unavailable if too few clusters remain. No field collection application is implemented.

Prespecified subset sensitivity now reports estimates excluding logged starts in the preceding 24 h, starts in the fixed outcome period, both, and sessions without confirmed absence of technical failure. These are descriptive selection-sensitive comparisons, not causal adjustments; absence of a log is not proof of absence of creation. See ethics-protocol.md for approval gates. No field collection has been enabled.

## Fixed-family and bootstrap reporting gates

Optional secondary models retain their prespecified three slots even if one model cannot be estimated. The two relief terms share a model; missing/constant brooding does not suppress valid relief terms. Holm uses p=1 internally for unavailable slots, with null adjusted p and reason in the output. Invalid supplied scores fail closed. Bootstrap percentile intervals are withheld unless at least 499 draws were requested and 90% of draws jointly succeeded; point estimates and failure counts remain. The joint-fit implementation reports shared draw accounting for every method, not independent method-specific failures. The new calibration driver records conditional and operational coverage against the complete-outcome reference for both IPW caps and all 15 shift scenarios, bias/MCSE and interval availability. A shift envelope is not a CI. These gates do not establish coverage, nor authorize numerical imputation of genuinely undefined outcomes; the endpoint-state decision remains separate.

## Candidate empirical cessation gate

Empirical CLI requires both authorized enrollment and check-in ledgers, with frozen IANA timezone, exact offset-aware cessation time (or explicit blank), first fully inactive day and check-in timestamp. `withdrawal_audit.py` checks every event before model execution, including follow-ups of earlier sessions; at or after cutoff fails. Calendar consistency is checked before fitting. Missing response timestamps and unknown IDs block inference. Synthetic mode preserves historical fixture behavior. No code authorizes retention or confirmation; actual university policy and consent must be agreed before fieldwork.

## Endpoint ascertainment candidate

The ledger separates defined (timely matched activity still relevant or prevented by barriers), undefined (timely matched activity independently no longer applicable), and unknown (no timely matched relevance/status evidence). No assumption that nonresponse implies a defined endpoint. The original complete-case model is descriptive among observed defined sessions if other states exist; full-session IPW/shift/bootstrap is withheld, not silently restricted to a selected population. Confirm the status wording and estimand with the owner and pilot. Existing synthetic calibration arrays without endpoint_state assume all outcomes defined; historical numbers do not validate this new ascertainment gate.
