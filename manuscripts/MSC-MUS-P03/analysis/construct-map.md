# P03 construct-to-item contract v0.2.0

Scientific owner: Mateusz Pomianek. Candidate wording, not validated measures. All psychological answers are retrospective within one cross-sectional survey. A time anchor is a reference in memory, not a prospective measurement.

| Construct | Polish candidate item or field | Response / time anchor | Analysis field | Interpretation |
|---|---|---|---|---|
| Expression motive | Na ile przed rozpoczęciem sesji chciałeś/aś wyrazić swoje emocje? | 0–10, recalled before | motive_expression | H1 predictor, not accomplished expression |
| Mood motive | Na ile przed rozpoczęciem sesji chciałeś/aś poprawić swój nastrój? | 0–10, recalled before | motive_mood | H2 predictor, not observed regulation |
| Exploration motive | Na ile przed rozpoczęciem sesji chciałeś/aś odkryć nowe możliwości muzyczne? | 0–10, recalled before | motive_explore | H3 predictor |
| Entertainment motive | Na ile przed rozpoczęciem sesji chciałeś/aś dobrze się bawić? | 0–10, recalled before | motive_fun | Covariate |
| Perceived ease of understanding emotions | Tuż przed rozpoczęciem sesji, na ile łatwo było Ci zrozumieć własne emocje? | 0 very difficult to 10 very easy, recalled before | clarity_pre | H1 covariate; not objective clarity |
| Perceived ease of understanding emotions | Tuż po zakończeniu sesji, na ile łatwo było Ci zrozumieć własne emocje? | Same anchors, recalled after | clarity_post | H1 outcome; coefficient in rating points |
| Affective valence | Tuż przed rozpoczęciem sesji, jak przyjemny lub nieprzyjemny był Twój stan emocjonalny? | 0 very unpleasant, 5 neutral, 10 very pleasant, recalled before | valence_pre | H2 covariate |
| Affective valence | Tuż po zakończeniu sesji, jak przyjemny lub nieprzyjemny był Twój stan emocjonalny? | Same anchors, recalled after | valence_post | H2 outcome |
| Prompting | Czy w tej sesji formułowałeś/aś polecenie lub tekst? | yes/no/skip, during | prompted | Separate descriptive indicator |
| Regeneration | Czy w tej sesji ponownie generowałeś/aś wariant utworu? | yes/no/skip, during | regenerated | H3 component |
| Selection | Czy w tej sesji wybierałeś/aś spośród wariantów? | yes/no/skip, during | selected | H3 component |
| Editing | Czy w tej sesji edytowałeś/aś lub rozszerzałeś/aś utwór? | yes/no/skip, during | edited | H3 component |
| Operation diversity | Derived, no separate item | Sum of three binary indicators, 0–3, only all observed | operation_diversity | H3 outcome; number of distinct operation types, not number of iterations or intensity |
| Perceived decisional influence | Na ile miałeś/aś poczucie wpływu na decyzje twórcze? | 0–10, recalled during | agency | H4 predictor; not objective control |
| Perceived personal significance | Na ile doświadczenie tej sesji miało dla Ciebie osobiste znaczenie? | 0–10, recalled experience | resonance (legacy code) | H4 outcome; not emotional resonance, aesthetic quality or efficacy |
| Perceived expression function | Na ile podczas sesji działanie umożliwiło Ci wyrażenie emocji? | 0–10 or skip/not applicable | function_expression | Descriptive function |
| Perceived exploration function | Na ile podczas sesji działanie umożliwiło Ci poznanie nowych możliwości? | Same | function_explore | Descriptive function |
| Perceived distraction function | Na ile podczas sesji działanie umożliwiło Ci oderwanie uwagi od trudnych myśli? | Same | function_distraction | Descriptive function, not avoidance |
| Perceived social function | Na ile podczas sesji działanie umożliwiło Ci poczucie więzi z innymi? | Same | function_social | Descriptive function |
| Frustration | Na ile odczuwałeś/aś frustrację podczas sesji? | 0–10 or skip | frustration | Descriptive experience |
| Difficulty disengaging | Na ile trudno było Ci zakończyć tę sesję, kiedy chciałeś/aś przestać? | 0–10 or skip/not applicable | difficulty_disengaging | Not rumination or clinical impairment |
| Age | Ile masz ukończonych lat? | integer >=18 | age | Covariate |
| Musical experience | Jak oceniasz swoje doświadczenie muzyczne? | 0–10 | experience | Self-rating, not objective expertise |
| Use days | W ilu dniach z ostatnich 30 dni korzystałeś/aś z generatora muzyki? | integer 0–30 | use_days | Covariate, not time or intensity |
| Episode recency | Ile dni temu odbyła się wybrana sesja? | integer 0–30 | recency | Covariate |
| Recruitment source | Approved recruitment channel metadata | university/community/other | source | Two indicators |

Retain historical code `iteration_count` only as an equal derived compatibility alias; H3 now uses `operation_diversity`. No historical estimate is changed. `resonance` remains a legacy field name and means personal significance only. For a future actual emotional-resonance construct use a separate piloted item asking emotional correspondence, not personal importance. For iteration intensity collect separate counts of generations/edits and elapsed time, not the diversity sum. Neither extension enters the current H1–H4.

Cognitive interviews: two prospective rounds totalling 8–12 volunteers, subject to approval. Ask respondents to paraphrase each target item, reconstruct the recall anchor, distinguish pre-session motive from subsequent function, distinguish ease of understanding from feeling better, distinguish personal significance from emotional correspondence, and recount cases with ten regenerations but one operation type, and abandoned sessions without an output. Record misunderstanding, retrieval difficulty, response-mapping difficulty, and revision rationale without personal narratives in Git. Repeat revised items in round two. No item freeze until material misunderstandings are addressed; no actual responses or ratings are claimed.
