# P03: prospective survey protocol (v0.1.0, 2026-11-26)

Owner: Mateusz Pomianek. Status: PROSPECTIVE; not preregistered or approved for recruitment. Target: Psychology of Music.

## Survey draft (Polish)
Do not show hypotheses to participants. Test comprehension with 8–12 volunteers, subject to appropriate ethics approval. Pilot data are excluded from confirmatory analysis. Final wording, permissions, timing and scoring must be frozen before recruitment.

1. Consent and eligibility: age ≥18; Polish-language comprehension; intentional generative music task in previous 30 days. Include abandoned attempts. No audio, lyrics or identifying handles.
2. Episode anchor: „Pomyśl o ostatniej sesji tworzenia muzyki z użyciem generatora AI, także jeżeli nie powstał gotowy utwór. Odpowiadaj wyłącznie w odniesieniu do tej sesji.” Record days since session and whether any output was produced.
3. Initial motives, four independent ratings, 0 (wcale) to 10 (bardzo silnie): „Na ile przed rozpoczęciem sesji chciałeś/aś: wyrazić swoje emocje; poprawić swój nastrój; odkryć nowe możliwości muzyczne; dobrze się bawić?” Include skip option.
4. Pre and post ratings, separate time anchors: „Tuż przed rozpoczęciem / tuż po zakończeniu sesji, na ile łatwo było Ci zrozumieć własne emocje?” 0 = bardzo trudno, 10 = bardzo łatwo. „Jak przyjemny lub nieprzyjemny był Twój stan emocjonalny?” 0 = bardzo nieprzyjemny, 5 = neutralny, 10 = bardzo przyjemny.
5. Operations: prompting/lyrics, regeneration, selection among variants, editing/extension. Each yes/no/skip. Record whether output completed.
6. Agency: „Na ile miałeś/aś poczucie wpływu na decyzje twórcze?” 0–10. Personal significance (legacy field resonance): „Na ile doświadczenie tej sesji miało dla Ciebie osobiste znaczenie?” 0–10.
7. Functions: „Na ile podczas sesji działanie umożliwiło Ci wyrażenie emocji, poznanie nowych możliwości, oderwanie uwagi od trudnych myśli, poczucie więzi z innymi?” Separate 0–10 ratings, not applicable/skip permitted. Optional adverse items: frustration, difficulty disengaging (0–10); no clinical interpretation.
8. Background: age, musical experience (0–10), generator-use days over 30 days (0–30), source of recruitment, broad platform category. No direct identifiers.

## Data contract
One row per participant. Mandatory P03 study code: `p03-` plus a random canonical lowercase UUIDv4 issued once by the approved survey intake, never derived from a personal identifier or an identifier from another study. Keep codes and participant records only in restricted institutional storage; no IP retention or direct identifiers. Import only authorized exports; withhold analysis of duplicate codes until adjudication, including a duplicate across an accepted and excluded row. An invalid or missing code among consented eligible submissions blocks analysis. Declined or malformed flags exclude that row before any response conversion; aggregate intake counts only, do not persist excluded sensitive answers. All unobserved values are NA, never zero. Core columns:

| Column | Type / range |
|---|---|
| study_id | mandatory canonical P03-prefixed lowercase UUIDv4 for accepted rows |
| eligible, consent | native Boolean or exact CSV tokens True/true, False/false; missing: blank or NA; all other tokens invalid |
| age | integer ≥18 |
| experience | 0–10 |
| use_days, recency | integer 0–30 |
| source | university, community, other |
| motive_expression, motive_mood, motive_explore, motive_fun | 0–10 each |
| clarity_pre, clarity_post, valence_pre, valence_post | 0–10 each |
| prompted, regenerated, selected, edited | Boolean or NA |
| agency, resonance | 0–10 |
| function_expression, function_explore, function_distraction, function_social | 0–10 or NA |
| frustration, difficulty_disengaging | 0–10 or NA |

Define operation_diversity = regenerated + selected + edited only if all three are observed; retain iteration_count solely as a compatibility alias. This is diversity of operation types, not count of iterations. The clarity fields represent recalled perceived ease of understanding emotions and resonance represents personal significance, not emotional resonance. See analysis/construct-map.md for the complete item contract and cognitive interview probes. Reject impossible values at entry; unresolved invalid values become NA. Document ineligible records and withdrawals without retaining their sensitive responses. No exclusions based on outcomes, response speed alone or failure to finish a song. No IP-based duplicate detection.

## Analysis freeze gates
- Verify Polish comprehensibility; check rights for any external instrument; do not describe custom indicators as validated scales.
- Confirm sample-size simulation under bounded ratings, correlated motives and missingness; freeze stopping rules.
- Implement complete-record OLS-HC3, Holm, ordered-model sensitivity, MAR multiple imputation and delta scenarios; test synthetic data before enrollment. Retain nonestimable ordinal thresholds even when the common-slope model fails. Pool a sensitivity scenario only if every prespecified imputation yields valid inference; report fit or pooling failures without replacing them with estimates. These diagnostics do not establish proportional odds, convergence or identification under MNAR.
- P03, P04 and P06 have separate participant identifiers, data dictionaries and intended cohorts. P03-S02 identifies only the P03 dataset. No automatic join or shared recruitment assumption; any cross-study linkage needs separate approved consent, protected linkage table, predefined estimands and disclosure of overlap. Prevent repeated submissions with a single-use study code where approved, not IP tracking; self-report prior participation and review conflicting codes outside the analysis pipeline.
- Obtain institutional review and preregistration. No fieldwork or claims of observed benefits yet.

## Source readiness
Schäfer et al. (2013), doi:10.3389/fpsyg.2013.00511, and Saarikallio (2008), doi:10.1177/102986490801200206, support music listening/function and mood regulation constructs, not equivalence to generative creation. He (2026), doi:10.3389/fpsyg.2026.1835406, is directly relevant to agency. Full-text audit and current systematic novelty search remain open; existing P02 bibliography entries are inherited and not independently audited here.

## Conditional recruitment plan

Target 500 complete eligible H1 records; conditional cap 660 submissions or eight weeks, whichever limit is reached first, subject to prospective approval. Historical cap 560 is a sensitivity scenario only. Before freeze use a separate approved feasibility sample to obtain the combined eligible-and-complete rate and one-sided 95% exact lower bound. Select a cap rounded upward to 20 with binomial assurance ≥.95 at that lower bound, separately assess throughput, costs and time limit, and obtain owner approval. If infeasible, retain NO-GO. Example scenarios are not pilot observations: at p=.794666, cap660 gives .99100; at p=.78, cap660 gives .92349; at p=.75, cap700 gives .98607; at p=.70, cap760 gives .99454. See analysis/recruitment_assurance.py. Never monitor effect estimates or change the cap after start.
