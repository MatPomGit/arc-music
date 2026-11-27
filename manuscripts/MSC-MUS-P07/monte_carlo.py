"""Local Monte Carlo launcher for MSC-MUS-P07. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":2,"pilot":100,"full":2000}[profile]
    ref={"smoke":10000,"pilot":40000,"full":100000}[profile]
    args=["--smoke"] if profile=="smoke" else []
    return [job("primary","simulation.py","--reps",reps,"--reference-n",ref,"--seed",20261218,*args),
            job("secondary","secondary_calibration.py","--reps",reps,"--seed",20261219,*args)]

if __name__=="__main__":main("P07")
