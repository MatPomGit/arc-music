"""Local Monte Carlo launcher for MSC-MUS-P06. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":2,"pilot":100,"full":2000}[profile]
    ref={"smoke":10000,"pilot":40000,"full":100000}[profile]
    draws={"smoke":49,"pilot":499,"full":999}[profile]
    return [job("cluster","cluster_calibration.py","--reps",reps,"--reference-n",ref,"--seed",20261215),
            job("bounded","bounded_simulation.py","--reps",reps,"--reference-n",ref,"--seed",20261216),
            job("missing","missing_calibration.py","--reps",reps),
            job("bootstrap","bootstrap_calibration.py","--reps",reps,"--bootstrap",draws,
                "--reference-n",ref,"--n",160,"--seed",20261217)]

if __name__=="__main__":main("P06")
