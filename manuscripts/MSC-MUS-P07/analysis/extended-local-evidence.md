# Extended P07 screen v0.11.0
Executed 27 November 2026, 72 cells × 200 replications, seed 20261206, 14400 synthetic datasets, 28800 valid endpoint fits and 28800 valid bound calculations, zero failures. Output complete=true, screening_only=true. Output SHA-256 542808914ac964180f7c02fd6806300ed6541d8a4e45ac19761e952f1456cf13 (73569 bytes); local environment Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0. Script blob 9a35336f3c729b09c02f99116e2f2c743e16ef5d matches the executed script byte-for-byte; local estimator and Holm routine were transcribed from the existing production implementations, not an exact full repository checkout. Exhaustive eight-completion bound check passed locally. The CI runs the repository implementation. Full output retained as separate local synthetic JSON; no full 2000-replication rerun claimed.

Joint alternative results: N, prevalence, response-stage mechanism, H2, H3, joint operational rejection.
| N | prevalence | mechanism | H2 | H3 | both |
|---:|---:|---|---:|---:|---:|
|480|.05|MCAR|.670|.660|.465|
|480|.05|MAR|.725|.595|.480|
|480|.05|joint MNAR|.175|.695|.160|
|480|.10|MCAR|.930|.910|.865|
|480|.10|MAR|.930|.900|.850|
|480|.10|joint MNAR|.385|.945|.375|
|640|.05|MCAR|.830|.825|.710|
|640|.05|MAR|.785|.745|.640|
|640|.05|joint MNAR|.325|.895|.300|
|640|.10|MCAR|.985|.970|.955|
|640|.10|MAR|.990|.980|.970|
|640|.10|joint MNAR|.540|.995|.540|
|1000|.05|MCAR|.975|.950|.930|
|1000|.05|MAR|.955|.885|.850|
|1000|.05|joint MNAR|.445|.975|.435|
|1000|.10|MCAR|1|1|1|
|1000|.10|MAR|1|1|1|
|1000|.10|joint MNAR|.700|.995|.700|

False-family range MCAR .015–.040, MAR .020–.050, joint MNAR .050–.405; max at N1000, .10, global null (81/200). H2/H3 coverage joint MNAR .400–.870/.670–.945; bias -.196963 to -.134368 / -.072767 to -.035839. In all 72 cells for both outcomes all 200 finite-design bounds include zero. Mean joint-MNAR bound widths 3.319614–3.743619 and 2.017306–2.216272. These are not confidence intervals and exclude unknown exposures. Preliminary screen, MCSE up to .0354, no recruitment authorization. N480 is a tested scenario, not a proposed sample (round proposed 480 to 500 under AGENTS.md).
