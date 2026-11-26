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
