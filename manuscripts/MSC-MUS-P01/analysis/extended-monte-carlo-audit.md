# Extended Monte Carlo audit (2026-11-26)
Simulation SHA: cee6e03d5f36103efb4ce084a76df0080cf13883. Run [45860229628](https://github.com/MatPomGit/arc-music/actions/runs/45860229628). All 12 jobs completed successfully. Downloaded all 12 artifacts, verified embedded SHA and 2,000 requested replications each. N=80, K=8, seed 76491. Each scenario had 2,000 valid mixed fits, 2,000 valid IPW fits, zero failures, and 199/199 bootstrap draws for its separate sensitivity dataset. The common seeds across effect scenarios imply common random numbers; do not pool scenarios as independent evidence.

| H | Missing | Truth | Artifact | Mixed bias | Mixed rejection | Mixed coverage | IPW bias | IPW rejection | IPW coverage | Mixed boundary count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H6 | complete | 0 | 15138825859 | -0.00334786 | 0.052 | 0.948 | 0.00092318 | 0.057 | 0.943 | 1 |
| H6 | complete | -0.25 | 15138446477 | -0.00334786 | 0.98 | 0.948 | 0.00092318 | 0.943 | 0.943 | 1 |
| H6 | MAR | 0 | 15139040260 | -0.00438786 | 0.0625 | 0.9375 | 0.00303174 | 0.07 | 0.93 | 7 |
| H6 | MAR | -0.25 | 15138701858 | -0.00438786 | 0.964 | 0.9375 | 0.00303174 | 0.87 | 0.93 | 7 |
| H6 | MNAR | 0 | 15138153044 | -0.03134732 | 0.0815 | 0.9185 | -0.03965984 | 0.0985 | 0.9015 | 6 |
| H6 | MNAR | -0.25 | 15139111958 | -0.03134745 | 0.9845 | 0.9185 | -0.03965984 | 0.954 | 0.9015 | 6 |
| H10 | complete | 0 | 15138017872 | 0.00036531 | 0.057 | 0.943 | 0.00038645 | 0.056 | 0.944 | 688 |
| H10 | complete | -0.35 | 15138925889 | 0.00036561 | 0.193 | 0.943 | 0.00038645 | 0.1945 | 0.944 | 675 |
| H10 | MAR | 0 | 15139165683 | -0.01060891 | 0.063 | 0.937 | 0.0161003 | 0.058 | 0.942 | 724 |
| H10 | MAR | -0.35 | 15138148336 | -0.01242575 | 0.133 | 0.9415 | 0.01679276 | 0.1 | 0.942 | 750 |
| H10 | MNAR | 0 | 15138204177 | 0.01157598 | 0.0505 | 0.9495 | 0.04480357 | 0.069 | 0.931 | 658 |
| H10 | MNAR | -0.35 | 15139625391 | 0.01587511 | 0.1315 | 0.9475 | 0.04789832 | 0.1045 | 0.9275 | 686 |

Rejection under null is type-I error, under alternative is nominal power (not adjusted for miscalibration). H6 MNAR null rejection .0815, Wilson 95% MC interval [.07030,.09431]; coverage .9185. IPW MNAR null rejection .0985, coverage .9015. H6 MAR mixed null rejection .0625, interval [.05271,.07397]. H10 complete-data power .193 [.17630,.21088]; MAR .133 [.11882,.14859]; MNAR .1315 [.11739,.14702]. H10 covariance-boundary counts 658–750 per 2,000 (32.9–37.5%); numerical convergence is not reliable covariance identification. H10 must not use this sample size for confirmation. Recalibrate finite-sample inference; investigate simpler covariance specifications and larger sample size, with justified effect, attrition, and precision targets. MNAR cannot be resolved by estimated MAR weights. No empirical participant effects or guarantee of type-I control. Original results remain tied to the simulation SHA even after text-only revisions. The complete JSON reports include Wilson intervals, bias MCSE, fixed-delta and IPW bootstrap intervals; artifact IDs above preserve provenance, but hosted artifacts have finite retention.

Manuscript CI [45860229688](https://github.com/MatPomGit/arc-music/actions/runs/45860229688) completed SUCCESS for the same SHA, validation artifact 15136869328: 20 pages, 6625 body words, weighted TeXcount 6988, no overfull or undefined reference/citation diagnostics found in main.log. New exact-head CI required after text changes. No independent review certified.
