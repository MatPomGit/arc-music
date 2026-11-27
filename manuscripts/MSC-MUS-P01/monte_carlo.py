"""Local Monte Carlo launcher for MSC-MUS-P01"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    return [job("cp-joint","cp_joint_power.py","--reps",{"smoke":100,"pilot":2000,"full":20000}[profile],"--seed",20261210)]

if __name__=="__main__":main("P01")
