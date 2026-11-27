"""Local Monte Carlo launcher for MSC-MUS-P02. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    return []  # Reflexive thematic analysis; no sampling-power simulation.

if __name__=="__main__":main("P02")
