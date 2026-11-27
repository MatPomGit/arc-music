# Program construct and cohort register v1.0.0

Scientific owner: Mateusz Pomianek. All rows prospective; no data collection, final measure freeze or ethics approval asserted. Dataset IDs reserve separate namespaces, not actual datasets. P01 prediction correspondence is recorded in [the proposition map](../manuscripts/MSC-MUS-P01/analysis/proposition-map.md); none of P02–P09 exactly tests an entire original prediction.

| Protocol / reserved dataset | Unit and population | Timing / construct and target | Role |
|---|---|---|---|
| P01 / AIM-ER-CP | Eligible randomized adults | Baseline/immediate goal attainment; goal × affordance, positive simple-effect conjunction; common candidate 0–10 scale | Conceptual design; no empirical dataset |
| P02 / MUS02-QUAL | Polish-speaking creators; interview corpus | Retrospective account anchored to most recent eligible episode, reflexive thematic analysis | Discovery, not effect estimation |
| P03 / MUS03-SURVEY | Eligible creators; one recalled episode/person | Initial expression motive vs recalled ease of understanding, adjusted regression; original 0–10 items | Observational H1, Holm secondary |
| P04 / MUS04-TRIAL | Eligible adults; randomized person | T0 PAQ-S-PL total, immediate production-plus-fit; assignment × observed total; separate clarity | Experimental H1, Holm H2/H3 |
| P05 / MUS05-EFA, MUS05-CFA, MUS05-RETEST | Adult creators; separate EFA/CFA persons, same episode for retest | 35 candidate AI-MRFS items (0–4); ordinal dimensionality and validity, retest 7–14 d | Psychometrics, independent samples; retest nested in CFA |
| P06 / MUS06-DIARY | Creators; naturally initiated session nested in person | Pre-session avoidance, interference during next 24 h; follow-up 24–28 h; within-person slope | Observational H1, Holm secondary; applicability gate |
| P07 / MUS07-EMA | Creators; prescheduled window nested in person | Baseline, 60/180 min; valence contrast in endpoint-specific observed switchers | Observational H1, Holm H2/H3; no trajectory/causal claim |
| P08 / MUS08-TRIAL | Adults; randomized person, 2 × 2 | Immediate heard-arrangement ownership and agency; authority main effect, interaction | Full-cohort endpoint BLOCKED; heard-only descriptive |
| P09 / MUS09-TRIAL | Adults; randomized person | T0/T1/day7; perceived understanding of one event, current perspective | Package contrast H1; Holm H2/H3; missingness candidate not approved |

Each protocol's main.tex and analysis or instrument folder define exact fields/versions. For P03 use the intake contract; P04 empirical.py; P06 withdrawal_audit.py and ledger.py; P07 schedule.py; P08 assignment_ledger.py; P09 export_schema.py. Contract tests are not institutional approval. Separate cohort codes, no cross-study linking by default. See [policy](data-policy.md) and [rights gates](rights-gates.md). Before any shared-sample analysis, register dataset/version, overlap counts, linkage authority, distinct estimand and analysis classification, and disclose overlap in each report. A pilot cannot enter its own confirmatory cohort. No repeated analysis of a shared cohort counts as independent replication.
