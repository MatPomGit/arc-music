"""Prospective P03 recruitment assurance; no participant data or authorization."""
import argparse
import json
from scipy.stats import binom, beta

TARGET=500
ASSURANCE=.95
CANDIDATE_CAP=660


def attainment(cap, complete_p, target=TARGET):
    if not isinstance(cap,int) or not isinstance(target,int) or cap<target or target<1 or not 0<=complete_p<=1:
        raise ValueError("Invalid cap, target or probability")
    return float(binom.sf(target-1,cap,complete_p))


def rounded_cap(complete_p, assurance=ASSURANCE, target=TARGET, limit=2000):
    if not 0<assurance<1 or not 0<complete_p<=1:
        raise ValueError("Invalid assurance or completeness")
    for cap in range(20*((target+19)//20),limit+1,20):
        if attainment(cap,complete_p,target)>=assurance:
            return cap
    return None


def pilot_lower(complete, submitted):
    if not isinstance(complete,int) or not isinstance(submitted,int) or not 0<=complete<=submitted or submitted<1:
        raise ValueError("Invalid pilot counts")
    return float(beta.ppf(.05,complete,submitted-complete+1)) if complete else 0.


def report():
    probabilities=[.70,.72,.74,.75,.76,.78,.79,.7946660955,.80,.82,.85,.90]
    return {"synthetic_planning":True,"recruitment_authorized":False,
            "target_complete":TARGET,"proposed_minimum_assurance":ASSURANCE,
            "candidate_cap":CANDIDATE_CAP,
            "assumption":"iid probability of eligible AND complete per submission; excludes eight-week limit",
            "scenarios":[{"complete_probability":p,
                          "candidate_attainment":attainment(CANDIDATE_CAP,p),
                          "minimum_rounded_cap":rounded_cap(p),
                          "historical_560_attainment":attainment(560,p)} for p in probabilities],
            "illustrative_pilot_uncertainty":[{"submitted":n,"complete":round(.8*n),
                    "one_sided_95_lower":pilot_lower(round(.8*n),n),
                    "cap_at_lower":rounded_cap(pilot_lower(round(.8*n),n))}
                    for n in (30,50,100,200)]}


if __name__=="__main__":
    print(json.dumps(report(),indent=2,allow_nan=False))
