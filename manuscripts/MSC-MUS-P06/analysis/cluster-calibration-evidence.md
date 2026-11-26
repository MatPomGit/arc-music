# Synthetic cluster calibration v0.5.0 (2026-11-26)

Executed in a local Python numerical environment using the bounded DGP and algebraically identical within-person estimator, single BLAS thread, seed 2606. 27 cells x 1000 independent datasets = 27000 replications; no failures. Three separate 100000-participant reference datasets (six sessions each). Six sessions/participant, 30% expected missingness, AR(1) rho=.4, random slope SD=.2, latent residual SD=1.5. Rounded 0–10 outcomes. Rounded results are preserved in cluster-calibration-results.csv. The committed script reconstructs the run; exact-head CI reproduction is separate and pending.

Compare full CR1 factor G/(G-1)*(N-1)/(N-G-p) with a candidate nested-cluster factor G/(G-1)*(N-1)/(N-p). Both use t(G-1). The coefficient is identical. The null reference estimate was .001131 (full SE .001328); the rejection target is zero. Nonzero reference observed-scale slopes were .148705 (SE .001322) and .293857 (SE .001319). These are finite reference estimates, not exact population parameters.

Under MCAR/MAR at latent zero, full correction rejects 2.2–3.2%, candidate 4.9–5.6%; full coverage 96.8–97.8%, candidate 94.4–95.1%. At n=160, MAR, latent slope .15, rejection is 95.6%/97.4% respectively. At n=80 it is 71.2%/79.6%. At n=240 it is 99.9%/99.9%. Monte Carlo SE at a 5% rate is about .0069; a rate of 100% in finite runs does not establish certainty.

Under MNAR at latent zero, candidate rejection rises to 8.3–8.5% for n=160/240; at latent .30, bias is approximately -.022 and candidate coverage is 88.1–90.9%. No variance correction removes selection bias. Rejection under MNAR is not reliable power for the complete-data target.

Decision: keep current full CR1 provisionally and evaluate the nested correction against CR2/cluster bootstrap in additional stress scenarios. n=160 is a conditional planning point, not a locked sample size. Need four/ten sessions, dropout, heterogeneous variance, selective reporting, alternative serial correlation, and substantive smallest effect justification. Assess IPW and pattern sensitivity under simulated missingness before finalizing. No empirical results.
