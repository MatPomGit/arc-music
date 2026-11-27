"""Local Monte Carlo launcher for MSC-MUS-P03. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":2,"pilot":30,"full":2000}[profile]
    m={"smoke":5,"pilot":10,"full":50}[profile]
    sweeps={"smoke":3,"pilot":5,"full":15}[profile]
    ref={"smoke":10000,"pilot":100000,"full":500000}[profile]
    return [job("mi-"+mechanism,"imputation_calibration.py","--mechanism",mechanism,
                "--reps",reps,"--m",m,"--sweeps",sweeps,"--target",500,"--cap",660,
                "--seed",20261211,"--reference-n",ref)
            for mechanism in ("complete","outcome_mar","predictor_mar","mixed_mar","outcome_mnar")]

if __name__=="__main__":main("P03")
