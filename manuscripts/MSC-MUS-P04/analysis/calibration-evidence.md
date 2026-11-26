# P04 calibration evidence
Prior run: https://github.com/MatPomGit/arc-music/actions/runs/45885514638
Head: 110ccb917b9bdeb62ab95a1360a35daee6bb8623
Artifact: 15149356247, SHA-256 cba550a610659fcf30eed52a05658d9b4330657a9ddb74651723771afd5f65fa.
The archive was inspected; simulation-results.json reports SYNTHETIC_DESIGN_ONLY. All 12 scenarios had 250 valid replications per method and no failures (3,000 generated data sets, two estimates per data set). Selected pooled MAR results:
| Randomised N | True interaction (points) | Missingness | Bias | Coverage | Rejection |
|---:|---:|---|---:|---:|---:|
|480|0|complete|.018|.960|.040|
|480|0|MAR|.026|.964|.036|
|480|0|MNAR|.209|.876|.124|
|480|.36|MAR|.015|.960|.288|
|1000|0|complete|-.010|.944|.056|
|1000|0|MAR|.021|.968|.032|
|1000|0|MNAR|.220|.748|.252|
|1000|.36|MAR|.013|.952|.528|
|1000|.36|MNAR|.228|.736|.928|

Monte Carlo uncertainty is non-negligible: Wilson 95% intervals read from the artefact are .0163-.0619 for rejection .032, .2022-.3093 for .252 and .4662-.5890 for .528. These scenarios do not identify the real missingness mechanism. In particular a larger sample can increase false rejection under MNAR. Nominal power for .36 points at N=1000 is insufficient under the synthetic MAR scenario. The candidate cap remains provisional. The new grid-based criterion is an interpretive guard, not a guarantee of correct MNAR inference. The new calibration explores three sample sizes and three raw interaction magnitudes plus MNAR null/alternative cases. It uses 120 replications per case and 10 imputations for bounded CI cost; larger confirmatory calibration with 50 imputations remains necessary. Values of .36/.54/.72 are design scenarios, not validated minimally important differences. The study cannot proceed as confirmatory until feasibility, endpoint wording, the smallest meaningful effect and missingness assumptions have been agreed before preregistration.

## Extended calibration, verified 2026-11-26
Run https://github.com/MatPomGit/arc-music/actions/runs/45886286691; head 41e2df389b9a644cabd898a677d8f481b745848f; artifact 15149860935; digest as reported by Actions sha256:d56010b206cd746a644a79e64e81b597c10af12497728e1430ca31f3bd2ae783. Downloaded archive exact-head.txt matches; inspected analysis/calibration-results.json. All 11 scenarios have 120 valid replications and zero failures (1320 synthetic datasets). 10 imputations per replication, not the confirmatory 50.
|N|True composite interaction|Mechanism|Nominal rejection|Grid robust|Coverage|
|---:|---:|---|---:|---:|---:|
|640|.36|MAR|.350|.0083|.9083|
|640|.54|MAR|.7333|.0500|.9917|
|640|.72|MAR|.8833|.2250|.9250|
|1000|.36|MAR|.5333|.0000|.9833|
|1000|.54|MAR|.8333|.1167|.9667|
|1000|.72|MAR|.9833|.4083|.9583|
|1600|.36|MAR|.7667|.0250|.9333|
|1600|.54|MAR|.9750|.0833|.9333|
|1600|.72|MAR|1.0000|.5083|.9417|
|1000|0|MNAR|.2750|.0000|.7250|
|1000|.54|MNAR|1.0000|.2167|.7667|

Selected exact Wilson MC95: N=1000, MAR .54, nominal [.7565,.8894], robust [.0708,.1863]; MNAR null nominal [.2030,.3609], robust [0,.0310]; N=1600, MAR .72, robust [.4200,.5961]. Zero robust false positives in one mechanism is not proof of control. Robust rejection need not be monotone across independently seeded scenarios. No candidate achieves 80% grid-robust rejection. For a meaningful raw interaction, distinguish nominal power from robustness and use missingness prevention plus stakeholder-justified sensitivity assumptions. Confirmatory recruitment remains blocked until elicitation and feasibility. Prior 3,000-replication simulation was also rerun successfully in this CI; this is replication of the same seeds, not 3,000 independent new draws.
