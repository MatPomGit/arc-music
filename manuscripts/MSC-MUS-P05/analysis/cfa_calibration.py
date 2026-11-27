"""Full 35-item synthetic smoke calibration, independent generated samples."""
import argparse,json
import numpy as np
from recovery import simulate
from ordinal_cfa import fit_cfa
from ordinal_reliability import omega_latent_response,omega_observed_sum

def run(reps=8,seed=20261127):
    rng=np.random.default_rng(seed)
    domains=np.repeat(np.arange(7),5)
    output=[]
    for n,loading,rho,skew,missing in [(500,.65,.35,False,0.),(500,.65,.35,True,.02),(500,.40,.80,True,0.)]:
        records=[]
        for i in range(reps):
            x=simulate(n,7,5,loading,rho,skew,missing,rng)
            x=x[np.isfinite(x).all(axis=1)]
            record={"replicate":i,"complete_n":len(x)}
            try:
                fit=fit_cfa(x,domains)
                record["diagnostics"] = fit.diagnostics
                if not fit.proper:
                    raise ArithmeticError("improper CFA")
                record.update(status="proper",loading_bias=float(fit.loadings.mean()-loading),
                    mean_absolute_loading_error=float(np.mean(abs(fit.loadings-loading))),
                    mean_factor_correlation_error=float(np.mean(abs(fit.phi[np.tril_indices(7,-1)]-rho))),
                    rms_residual=fit.rms_residual,
                    omega_latent=[omega_latent_response(fit.loadings[domains==d]) for d in range(7)],
                    omega_observed=[omega_observed_sum(fit.loadings[domains==d],fit.thresholds[domains==d]) for d in range(7)])
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                record.update(status="failure",reason=str(exc))
            records.append(record)
        good=[a for a in records if a["status"]=="proper"]
        output.append({"n":n,"loading":loading,"rho":rho,"skew":skew,"missing_mcar_per_item":missing,
                       "requested":reps,"proper":len(good),
                       "mean_loading_bias":float(np.mean([a["loading_bias"] for a in good])) if good else None,
                       "records":records})
    return {"label":"SYNTHETIC DEVELOPMENT ONLY; conditional-weight CFA, not WLSMV",
            "seed":seed,"items":35,"scenarios":output}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=8)
    a=p.parse_args()
    if a.reps<1: p.error("positive replication count required")
    print(json.dumps(run(a.reps),indent=2,allow_nan=False))
