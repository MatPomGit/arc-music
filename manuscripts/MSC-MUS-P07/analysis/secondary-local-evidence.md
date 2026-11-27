# P07 secondary calibration, local synthetic evidence v0.10.0

Supplied aggregate: secondary-full.json, 190656 bytes, SHA-256 c4baf161a22c864aa3abd92b358c08a1d06e599787e27884bcf4261273e8ec2a. Raw aggregate retained locally, not committed in this revision. Seed 20261205, 2000 replications per cell, complete=true, screening_only=false, SYNTHETIC_DEVELOPMENT. All 72 unique cells match the specified Cartesian grid. All 288000 H2/H3 fit attempts succeeded; validated target equality, count/denominator arithmetic, marginal MCSE, family rejection accounting and null-family availability. Association with source 02244d0 and merged main 6024049 follows run instructions and schema; actual local HEAD and environment were not embedded. No independent full rerun.

Joint alternative H2=.4, H3=-.2; operational probabilities:

| N | prevalence | mechanism | H2 | H3 | both |
|---:|---:|---|---:|---:|---:|
|160|.05|MCAR|.231|.2025|.072|
|160|.10|MCAR|.4405|.3825|.227|
|160|.25|MCAR|.7895|.7115|.5975|
|320|.05|MCAR|.478|.4515|.2755|
|320|.10|MCAR|.7895|.732|.613|
|320|.25|MCAR|.9825|.966|.9515|
|160|.05|MAR|.210|.188|.0655|
|160|.10|MAR|.422|.3695|.205|
|160|.25|MAR|.7485|.6965|.574|
|320|.05|MAR|.434|.3845|.224|
|320|.10|MAR|.7365|.6915|.548|
|320|.25|MAR|.9795|.953|.937|
|160|.05|MNAR|.077|.2885|.0405|
|160|.10|MNAR|.1475|.545|.1035|
|160|.25|MNAR|.329|.872|.313|
|320|.05|MNAR|.163|.5835|.1255|
|320|.10|MNAR|.3015|.8705|.2815|
|320|.25|MNAR|.6355|.9945|.6335|

| Mechanism | False-family rejection | H2 coverage | H3 coverage | H2 bias | H3 bias |
|---|---|---|---|---|---|
|MCAR|.0185–.0445|.953–.9685|.9545–.969|-.00380 to .00788|-.00600 to .00465|
|MAR|.0195–.0425|.954–.9695|.949–.9685|-.00614 to .00993|-.00631 to .00600|
|MNAR|.0275–.2905|.5765–.9415|.7995–.9555|-.19647 to -.13124|-.06772 to -.04339|

Worst family rejection: 581/2000, N320, prevalence .25, global null, MNAR; MCSE .0101515947. The response-stage labels do not imply globally MCAR/MAR because all scenarios include informative withdrawal. Marginal coverage is not simultaneous coverage. No final recruitment, empirical inference or proof of general error control. Reproduce using a new output path and record actual source HEAD, dependencies and raw-file digest.
