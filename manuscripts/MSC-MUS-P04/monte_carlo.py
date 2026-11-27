"""Local Monte Carlo launcher for MSC-MUS-P04. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":2,"pilot":20,"full":2000}[profile]
    m={"smoke":5,"pilot":10,"full":50}[profile]
    args=["--reps",reps,"--m",m,"--seed",20261212,"--include-composite-mar"]
    if profile=="smoke":args+=["--smoke"]
    return [job("joint","joint_calibration.py",*args)]

if __name__=="__main__":main("P04")
