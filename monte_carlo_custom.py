"""Interactive custom design: modify only supported production CLI parameters."""
from dataclasses import replace
import hashlib
import json
import os
import fnmatch

# Bounds reflect CLI contracts, not approved methodological choices.
FIELDS={
 "P01":{},
 "P03":{"--m":(2,500,50),"--sweeps":(1,1000,15),"--target":(50,100000,500),
        "--cap":(50,100000,660),"--reference-n":(1000,10000000,500000)},
 "P04":{"--m":(2,500,50)},
 "P05":{"--pa-reps":(1,10000,500),"--n":(100,100000,500)},
 "P06":{"--reference-n":(100,10000000,100000),"--bootstrap":(1,100000,999),
        "--n":(10,100000,160)},
 "P07":{"--reference-n":(100,10000000,100000)},
 "P08":{"--reference-n":(100,10000000,100000),"--draws":(199,100000,1999)},
 "P09":{"--draws":(199,100000,999)},
}
LABELS={"--m":"Liczba imputacji","--sweeps":"Iteracje imputacji",
        "--target":"Docelowa liczba kompletnych rekordow N","--cap":"Limit rekrutacji",
        "--reference-n":"Liczebnosc proby referencyjnej",
        "--pa-reps":"Permutacje analizy rownoleglej","--n":"Liczebnosc N (tylko zadania z opcja N)",
        "--bootstrap":"Losowania bootstrap","--draws":"Losowania bootstrap"}

def integer(label,low,high,default=None):
    while True:
        prompt=f"{label} [{low}..{high}]"+(f" (Enter={default})" if default is not None else "")+": "
        raw=input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            n=int(raw)
            if low<=n<=high:
                return n
        except ValueError:
            pass
        print("Nieprawidlowa wartosc.")

def build(study,reps,seed,options,pattern="*"):
    from monte_carlo_runner import load_plan
    if study=="P02":
        return []
    if not 2<=reps<=100000 or not 0<=seed<=2**32-1:
        raise ValueError("Invalid replication count or seed")
    if set(options)-set(FIELDS[study]):
        raise ValueError("Unsupported option")
    for k,v in options.items():
        low,high,_=FIELDS[study][k]
        if not isinstance(v,int) or not low<=v<=high:
            raise ValueError("Invalid "+k)
    if study=="P03" and options.get("--target",500)>options.get("--cap",660):
        raise ValueError("Target exceeds cap")
    if study=="P08" and options.get("--reference-n",100000)%4:
        raise ValueError("P08 reference N must be divisible by 4")
    # Work from full grid; rebuild shard dependencies with exact denominators.
    tasks=load_plan(study,"full")
    if study in ("P05","P09"):
        groups={}
        for t in tasks:
            family=t.name.rsplit("/",1)[0]
            groups.setdefault(family,[]).append(t)
        rebuilt=[]
        for family,group in groups.items():
            first=next(t for t in group if not t.deps)
            agg=next(t for t in group if t.deps)
            if not (fnmatch.fnmatchcase(family,pattern) or fnmatch.fnmatchcase(agg.name,pattern)):
                continue
            batch=5 if study=="P05" and family.startswith("structure/") else 20
            keys=[]
            for start in range(0,reps,batch):
                name=f"{family}/shard-{start:05}"
                keys.append(name)
                a=list(first.args)
                count=min(batch,reps-start)
                if a[0]=="shard":
                    a[2:4]=[str(start),str(count)]
                else:
                    a[a.index("--offset")+1]=str(start)
                    a[a.index("--reps")+1]=str(count)
                rebuilt.append(replace(first,name=name,args=tuple(a)))
            a=list(agg.args);a[a.index("--expected")+1]=str(reps)
            rebuilt.append(replace(agg,args=tuple(a),deps=tuple(keys)))
        tasks=rebuilt
    else:
        tasks=[t for t in tasks if fnmatch.fnmatchcase(t.name,pattern)]
    if not tasks:
        raise ValueError("No matching simulation scenarios")
    output=[]
    for t in tasks:
        a=list(t.args)
        changes=dict(options)
        if not t.deps:
            changes["--seed"]=seed
            if study not in ("P05","P09"):
                changes["--reps"]=reps
        for key,val in changes.items():
            if key in a:
                a[a.index(key)+1]=str(val)
        output.append(replace(t,args=tuple(a)))
    return output

def interactive(study):
    from monte_carlo_runner import ROOT,load_plan,run_study,json_text
    from monte_carlo_results import describe_plan
    if study=="P02":
        print("P02: NOT_APPLICABLE (qualitative design)")
        return 0
    try:
        print("Wlasna symulacja syntetyczna. Nie zmienia protokolu badania.")
        reps=integer("Replikacje na scenariusz",2,100000)
        seed=integer("Ziarno generatora",0,2**32-1,20261227)
        jobs=integer("Procesy rownolegle",1,os.cpu_count() or 1)
        threads=integer("Watki BLAS na proces",1,max(1,(os.cpu_count() or 1)//jobs),1)
        tasks=load_plan(study,"full")
        names=[t.name for t in tasks if not t.deps] if study not in ("P05","P09") else [t.name.rsplit("/",1)[0] for t in tasks if t.deps]
        print("0: wszystkie scenariusze")
        for i,name in enumerate(names,1):
            print(f"{i}: {name}")
        choice=integer("Scenariusz",0,len(names))
        pattern=names[choice-1] if choice else "*"
        options={}
        while True:
            for k,(lo,hi,default) in FIELDS[study].items():
                options[k]=integer(LABELS[k],lo,hi,default)
            try:
                configured=build(study,reps,seed,options,pattern)
                break
            except ValueError as exc:
                print(exc)
        config={"study":study,"reps":reps,"seed":seed,"options":options,"pattern":pattern,
                "jobs":jobs,"threads":threads}
        run_id="custom-"+hashlib.sha256(json_text(config).encode()).hexdigest()[:16]
        print(json_text(config))
        describe_plan(study,"custom",configured)
        print("Run ID:",run_id)
        if input("Uruchomic? [t/N]: ").strip().lower() not in ("t","tak","y","yes"):
            return 0
        return 0 if run_study(study,"custom","*",jobs,threads,ROOT/"build"/"monte-carlo",run_id,custom=configured) else 1
    except (KeyboardInterrupt,EOFError):
        print("\nAnulowano.")
        return 130
