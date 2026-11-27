"""Local Monte Carlo launcher for MSC-MUS-P08. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":2,"pilot":100,"full":2000}[profile]
    ref={"smoke":10000,"pilot":40000,"full":100000}[profile]
    draws={"smoke":199,"pilot":499,"full":1999}[profile]
    args=["--smoke"] if profile=="smoke" else []
    return [job("factorial","simulation.py","--reps",reps,"--reference-n",ref,"--seed",20261220,*args),
            job("nonhearing","simulation.py","--reps",reps,"--reference-n",ref,"--seed",20261221,"--nonadherence",.15,*args),
            job("bootstrap","bootstrap_calibration.py","--reps",reps,"--draws",draws,"--seed",20261222,"--jobs",1)]

if __name__=="__main__":main("P08")
