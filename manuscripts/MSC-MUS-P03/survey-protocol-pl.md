# P03: prospective survey protocol (v0.1.0, 2026-11-26)

Owner: Mateusz Pomianek. Status: PROSPECTIVE; not preregistered or approved for recruitment. Target: Psychology of Music.

## Survey draft (Polish)
Do not show hypotheses to participants. Test comprehension with 8–12 volunteers, subject to appropriate ethics approval. Pilot data are excluded from confirmatory analysis. Final wording, permissions, timing and scoring must be frozen before recruitment.

1. Consent and eligibility: age ≥18; Polish-language comprehension; intentional generative music task in previous 30 days. Include abandoned attempts. No audio, lyrics or identifying handles.
2. Episode anchor: „Pomyśl o ostatniej sesji tworzenia muzyki z użyciem generatora AI, także jeżeli nie powstał gotowy utwór. Odpowiadaj wyłącznie w odniesieniu do tej sesji.” Record days since session and whether any output was produced.
3. Initial motives, four independent ratings, 0 (wcale) to 10 (bardzo silnie): „Na ile przed rozpoczęciem sesji chciałeś/aś: wyrazić swoje emocje; poprawić swój nastrój; odkryć nowe możliwości muzyczne; dobrze się bawić?” Include skip option.
4. Pre and post ratings, separate time anchors: „Tuż przed rozpoczęciem / tuż po zakończeniu sesji, na ile łatwo było Ci zrozumieć własne emocje?” 0 = bardzo trudno, 10 = bardzo łatwo. „Jak przyjemny lub nieprzyjemny był Twój stan emocjonalny?” 0 = bardzo nieprzyjemny, 5 = neutralny, 10 = bardzo przyjemny.
5. Operations: prompting/lyrics, regeneration, selection among variants, editing/extension. Each yes/no/skip. Record whether output completed.
6. Agency: „Na ile miałeś/aś poczucie wpływu na decyzje twórcze?” 0–10. Resonance: „Na ile doświadczenie tej sesji miało dla Ciebie osobiste znaczenie?” 0–10.
7. Functions: „Na ile podczas sesji działanie umożliwiło Ci wyrażenie emocji, poznanie nowych możliwości, oderwanie uwagi od trudnych myśli, poczucie więzi z innymi?” Separate 0–10 ratings, not applicable/skip permitted. Optional adverse items: frustration, difficulty disengaging (0–10); no clinical interpretation.
8. Background: age, musical experience (0–10), generator-use days over 30 days (0–30), source of recruitment, broad platform category. No direct identifiers.

## Data contract
One row per participant, random study ID, no contact details. All unobserved values are NA, never zero. Core columns:

| Column | Type / range |
|---|---|
| eligible, consent | Boolean |
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

Define iteration_count = regenerated + selected + edited only if all three are observed. Reject impossible values at entry; unresolved invalid values become NA. Document ineligible records and withdrawals without retaining their sensitive responses. No exclusions based on outcomes, response speed alone or failure to finish a song. No IP-based duplicate detection.

## Analysis freeze gates
- Verify Polish comprehensibility; check rights for any external instrument; do not describe custom indicators as validated scales.
- Confirm sample-size simulation under bounded ratings, correlated motives and missingness; freeze stopping rules.
- Implement complete-record OLS-HC3, Holm, ordered-model sensitivity, MAR multiple imputation and delta scenarios; test synthetic data before enrollment.
- Record dataset linkage to S02 and distinct primary estimands for P04/P06; no independent replication claims.
- Obtain institutional review and preregistration. No fieldwork or claims of observed benefits yet.

## Source readiness
Schäfer et al. (2013), doi:10.3389/fpsyg.2013.00511, and Saarikallio (2008), doi:10.1177/102986490801200206, support music listening/function and mood regulation constructs, not equivalence to generative creation. He (2026), doi:10.3389/fpsyg.2026.1835406, is directly relevant to agency. Full-text audit and current systematic novelty search remain open; existing P02 bibliography entries are inherited and not independently audited here.
