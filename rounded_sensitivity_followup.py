"""Independent-seed follow-up to completed rounded sensitivity screen."""
import argparse
import json
from rounded_sensitivity_calibration import load_path, p03, p08, p09

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",choices=("P03","P08","P09"),required=True)
    p.add_argument("--n",type=int,required=True)
    p.add_argument("--mechanism",required=True)
    p.add_argument("--effect",choices=("null","alternative"),required=True)
    p.add_argument("--reps",type=int,required=True)
    p.add_argument("--draws",type=int,required=True)
    a=p.parse_args()
    if a.reps<2 or a.draws<199:
        p.error("Invalid replication count")
    load_path(a.study)
    seed=20261203
    if a.study=="P03":
        results=p03(a.mechanism,a.reps,seed,sweeps=60)
    elif a.study=="P08":
        results=p08(a.n,a.mechanism,a.reps,a.draws,seed)
    else:
        results=p09(a.n,a.mechanism,a.effect,a.reps,a.draws,seed)
    print(json.dumps(dict(synthetic=True,screening_only=True,study=a.study,
                          seed=seed,results=results),indent=2,allow_nan=False))
