# Actual P09 candidate: independent precision screen v1.0.0

Synthetic only. Run 46017681854, exact source 0bf50ebaeae35492f5cd7a59847b1b9016396786, seed 20261207. Four cells, 20 independent datasets each, indices 0..19 (two shards), 999 refitted bootstrap draws per endpoint, standard outcome profile, stratified blocks. All targets stipulated defined. All 240 endpoint estimates and 239,760 bootstrap fits available. Each archive's HEAD, metadata, contiguous indices, raw CI coverage and rejection counts checked independently.

| Cell | N, mechanism, effect | ZIP artifact | SHA-256 |
|---|---|---:|---|
| 6 | 440 MAR global null | 15207720315 | 6d7d6f6139dab4234e0712dd2799e923c9f02e22ee83f6dd88a698a889dcd335 |
| 8 | 440 MAR H3=.5 only | 15206736976 | e54a2eb9be6732dd6dcf50ec1136757af24a42a3fb08f6b259b4ee88cccb7fde |
| 18 | 600 MAR global null | 15207381598 | 9ae1bd3a7214e7f4f73fde46f895cc233f129492247acbdb1a483e392e733b27 |
| 21 | 600 MNAR global null | 15207406827 | 45ab0304a9958a3fa91de4f5efa06d5acb28fa30d321cc299c92b6f570bff23d |

All denominators 20; conditional and operational counts coincide here.

| Cell | H1/H2/H3 coverage | Unadjusted H1/H2/H3 rejection | Holm H2/H3 rejection | True-null secondary FWER |
|---|---|---|---|---|
| 6 | 19/19/18 | 1/1/2 | 0/1 | 1 |
| 8 | 19/18/20 | 1/2/7 | 1/6 | 1 |
| 18 | 18/20/20 | 2/0/0 | 0/0 | 0 |
| 21 | 18/17/18 | 2/3/2 | 2/2 | 4 |

| Cell | H1/H2/H3 mean bias (points) |
|---|---|
| 6 | .00080 / -.04007 / .01280 |
| 8 | -.01774 / -.06019 / -.05399 |
| 18 | -.02786 / .05275 / -.04277 |
| 21 | .07490 / .10859 / -.04366 |

Wilson interval for 1/20: [.009,.236]; 2/20: [.028,.301]; 4/20: [.081,.416]; 6/20: [.145,.519]. At zero of 20, upper limit .161, not evidence of zero risk. Repeated CI with same seed is reproduction, not additional independent outer replication. Do not combine duplicated runs.

Decision: NO-GO for confirmatory adoption. MAR error and coverage uncertainty remains large; limited H3 detection at the hypothetical alternative; MNAR bias/family error persists. The four cells do not assess H1 alternative power, low overlap or actual target-status failures. At least 2,000 independent outer datasets per retained configuration and >=999 inner draws are proposed precision targets, not authorization or evidence of adequacy. Prioritize a substantively justified H1 effect and an explicitly specified outcome-regression/augmented candidate comparison; preserve the current IPW candidate and MNAR sensitivity as distinct methods. Owner/measurement/retention approvals remain prerequisites.
