"""Synthetic familywise error and power screen; no empirical data."""
import argparse,json
import numpy as np
from validity import validity_family,domain_score
from robust_calibration import wilson

def generate(n,rho,rng):
    # Seven latent domains and distinct imperfect comparator measurements.
    phi=np.full((7,7),.20); np.fill_diagonal(phi,1.)
    latent=rng.multivariate_normal(np.zeros(7),phi,size=n)
    x=np.digitize(.65*latent[:,:,None]+np.sqrt(1-.65**2)*rng.normal(size=(n,7,5)),[-.85,-.25,.25,.85])
    names=("EXP","REF","MOD","DIV","SOC","PER","AVO")
    scores={name:domain_score(x[:,j,:],authorized=True) for j,name in enumerate(names)}
    def comparator(j):
        return rho*latent[:,j]+np.sqrt(1-rho*rho)*rng.normal(size=n)
    pre=rng.normal(size=n)
    comparators={"expression":comparator(0),"clarity_pre":pre,
                 "clarity_post":.6*pre+comparator(1),"mood":comparator(2),
                 "rumination":comparator(5),"avoidance":comparator(6),
                 "use_frequency":rng.normal(size=n)}
    return scores,comparators

def run(reps=30,boot=199,seed=20261126):
    rng=np.random.default_rng(seed); scenarios=[]
    for n in (250,400,500,650,800):
        for rho in (0.,.25):
            records=[]
            for i in range(reps):
                scores,comparators=generate(n,rho,rng)
                row=validity_family(scores,comparators,authorized=True,reps=boot,seed=seed+i)
                records.append(row)
            rates={}
            for name in records[0]:
                rejections=sum(x[name]["supports_directional_hypothesis"] for x in records)
                rates[name]={"directional_rejections":rejections,"rate":rejections/reps,
                             "interval":wilson(rejections,reps),
                             "unavailable":sum(x[name]["status"]!="estimated" for x in records)}
            any_reject=sum(any(v["holm_p"]<=.05 for v in x.values()) for x in records)
            all_positive=sum(all(v["supports_directional_hypothesis"] for v in x.values()) for x in records)
            scenarios.append({"n":n,"latent_comparator_association":rho,"requested":reps,
                              "any_two_sided_rejection":any_reject/reps,
                              "any_rejection_interval":wilson(any_reject,reps),
                              "all_directional_rejections":all_positive/reps,"contrasts":rates})
    return {"label":"SYNTHETIC DEVELOPMENT; latent association is not observed-score effect",
            "seed":seed,"bootstrap_reps":boot,"scenarios":scenarios}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--reps",type=int,default=30)
    p.add_argument("--boot",type=int,default=199); a=p.parse_args()
    if a.reps<1 or a.boot<199: p.error("invalid replication counts")
    print(json.dumps(run(a.reps,a.boot),indent=2,allow_nan=False))
