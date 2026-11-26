# Verified PAQ-S synthetic calibration evidence
Date: 2026-11-26. No human-participant data.
## Measurement error
Run https://github.com/MatPomGit/arc-music/actions/runs/45889492136; artifact 15150727691; reported digest sha256:9d4991041c1bbeea18002febf954b8755bb7006c26bd2b47096ce42101f9fa95. Downloaded archive measurement-head.txt = 7ece9ac84bc64ffef6e14b7613afff42ea425c84; measurement-results.json inspected. All 12 scenarios: 300 valid per method, zero failed, 3,600 datasets. Reference 200,000 cases per noise setting. 
|Noise SD|Latent-score r|r MCSE|Observed target for latent .60|
|---:|---:|---:|---:|
|.5|.966369|.000114|.579821|
|.9|.907428|.000440|.544457|
|1.4|.804832|.000667|.482899|
|N|Latent interaction|Noise|Observed rejection|Oracle rejection|Observed coverage|
|---:|---:|---:|---:|---:|---:|
|640|0|.5|.0367|.0500|.9633|
|640|0|.9|.0500|.0267|.9500|
|640|0|1.4|.0500|.0500|.9500|
|640|.60|.5|.9200|.9400|.9567|
|640|.60|.9|.8433|.9167|.9467|
|640|.60|1.4|.8367|.9667|.9667|
|1000|0|.5|.0567|.0400|.9433|
|1000|0|.9|.0567|.0567|.9433|
|1000|0|1.4|.0700|.0667|.9300|
|1000|.60|.5|.9800|.9867|.9500|
|1000|.60|.9|.9600|.9867|.9367|
|1000|.60|1.4|.9200|.9800|.9433|
Selected Wilson MC95: N=640, .60, high noise observed rejection [.790627,.874194]; N=1000, null high noise [.046237,.104636]. No empirical PAQ-S reliability inferred. Complete-outcome DGP cannot establish joint power under missingness. Targets distinguish observed and oracle regression.
## Completion dependent, 50 imputations
Run https://github.com/MatPomGit/arc-music/actions/runs/45888642713; artifact 15151041277; reported digest sha256:063318ddfb6d058a0bd149fccb7f5b986d524ebc3e5e86b81fd2744f628b9d31. Downloaded completion-head.txt = 50192c297a709a53f75b0f637c2d702a6125537d; completion-results.json inspected. Six scenarios, all 120 paired valid, zero failures per method; 720 datasets and 2160 method evaluations. N=1000, 50 imputations.
Each method cell is nominal rejection / grid-robust rejection / coverage.
|Mechanism|True observed interaction|Baseline PMM|Status PMM|Enhanced status PMM|
|---|---:|---|---|---|
|status|0|.0333/.0000/.9667|.0417/.0000/.9583|.0583/.0000/.9417|
|status|.54|.8917/.2000/.9417|.9333/.2083/.9417|.9167/.2667/.9500|
|status|.72|1/.5500/.9583|1/.5833/.9500|1/.7083/.9583|
|outcome|0|.1000/.0000/.9000|.1000/.0000/.9000|.1000/.0000/.9000|
|outcome|.54|.9667/.3083/.8917|.9750/.3000/.9000|.9583/.4167/.9000|
|outcome|.72|.9917/.6917/.8917|.9917/.7000/.8917|1/.7917/.9167|
Selected Wilson MC95: status .72 enhanced robust [.621558,.782184]; outcome null nominal [.058134,.166682], robust [0,.031019]; outcome .72 enhanced robust [.710523,.854716]. Under outcome-dependent null, baseline and enhanced bias .0705 and .0796 points. For status .54, baseline and enhanced missing outcome fractions .1651 and .1392; missing status .1058 and .0203. Enhanced capture does not remove outcome-dependent bias. Elevated rejection under MNAR is not valid power evidence. Retain primary estimator; supplementary status model and capture remain sensitivities. No scenario justifies an approved sample size or a universal MNAR error-control claim. Numerical results are synthetic, not participant outcomes.
