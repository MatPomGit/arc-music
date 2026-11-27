"""Local Monte Carlo launcher for MSC-MUS-P09. Synthetic only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from monte_carlo_runner import job,main

def plan(profile):
    reps={"smoke":2,"pilot":20,"full":2000}[profile]
    draws={"smoke":199,"pilot":999,"full":999}[profile]
    batch={"smoke":2,"pilot":10,"full":20}[profile]
    cells=(6,8,18,21) if profile!="full" else range(40)
    tasks=[]
    for i in cells:
        name=f"ipw/cell-{i:02}"
        shards=[]
        for start in range(0,reps,batch):
            key=f"{name}/shard-{start:05}"
            shards.append(key)
            tasks.append(job(key,"candidate_shards.py","shard",i,start,min(batch,reps-start),
                             "--seed",20261223,"--draws",draws))
        tasks.append(job(name+"/aggregate","candidate_shards.py","aggregate","@OUT@/"+name,
                         "--expected",reps,deps=shards))
    for i in ((19,) if profile=="smoke" else (6,8,18,19,21,24,28,32,36)):
        name=f"paired/cell-{i:02}"
        shards=[]
        for start in range(0,reps,batch):
            key=f"{name}/shard-{start:05}"
            shards.append(key)
            tasks.append(job(key,"compare_candidates.py","--cell",i,"--offset",start,
                             "--reps",min(batch,reps-start),"--draws",draws,"--seed",20261224))
        tasks.append(job(name+"/aggregate","compare_candidates.py","--aggregate","@OUT@/"+name,
                         "--expected",reps,deps=shards))
    return tasks

if __name__=="__main__":main("P09")
