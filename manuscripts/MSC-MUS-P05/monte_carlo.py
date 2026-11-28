"""Local Monte Carlo launcher for MSC-MUS-P05. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":1,"pilot":20,"full":2000}[profile]
    pa={"smoke":10,"pilot":50,"full":500}[profile]
    tasks=[]
    structure_batch={"smoke":1,"pilot":5,"full":5}[profile]
    for structure in ("one_factor","higher_order","correlated_seven"):
        name=f"structure/{structure}"
        shards=[]
        for start in range(0,reps,structure_batch):
            key=f"{name}/shard-{start:05}"
            shards.append(key)
            tasks.append(job(key,"alternative_model_calibration.py","--structure",structure,
                "--n",500,"--reps",min(structure_batch,reps-start),"--pa-reps",pa,
                "--offset",start,"--seed",20261213))
        tasks.append(job(name+"/aggregate","alternative_model_calibration.py",
                         "--aggregate","@OUT@/"+name,"--expected",reps,deps=shards))
    cells=[(0,"invariant"),(1,"loading_dif"),(2,"threshold_dif"),(3,"intercept_dif")] if profile=="smoke" else [(i,s) for i in range(4) for s in ("invariant","threshold_dif","loading_dif","intercept_dif")]
    batch={"smoke":1,"pilot":5,"full":20}[profile]
    for i,scenario in cells:
        name=f"invariance/{i}-{scenario}"
        shards=[]
        for start in range(0,reps,batch):
            key=f"{name}/shard-{start:05}"
            shards.append(key)
            tasks.append(job(key,"invariance_reference_calibration.py","--size-index",i,
                "--scenario",scenario,"--reps",min(batch,reps-start),"--offset",start,
                "--seed",20261214))
        tasks.append(job(name+"/aggregate","invariance_reference_calibration.py",
                         "--aggregate","@OUT@/"+name,"--expected",reps,deps=shards))
    return tasks

if __name__=="__main__":main("P05")
