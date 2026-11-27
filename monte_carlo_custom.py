"""Interactive custom design: modify only supported production CLI parameters."""
from dataclasses import replace
import hashlib
import json
import os
import fnmatch
import math

# Bounds reflect CLI contracts, not approved methodological choices.
FIELDS={
 "P01":{},
 "P03":{"--m":(2,500,50),"--sweeps":(1,1000,15),"--target":(50,100000,500),
        "--cap":(50,100000,660),"--reference-n":(1000,10000000,500000)},
 "P04":{"--m":(2,500,50)},
 "P05":{"--pa-reps":(10,10000,500),"--n":(100,100000,500)},
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

def build(study,reps,seed,options,pattern="*",design=None):
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
    if design is not None:
        output=apply_design(study,output,design)
    return output

def apply_design(study,tasks,d):
    allowed={"P01":{"cp-joint"},"P03":{t.name for t in tasks if t.name.startswith("mi-")},"P04":{"joint"},"P05":{t.name for t in tasks if t.name.startswith("structure/")},"P06":{"bounded"},"P07":{"primary"},"P08":{"factorial","nonhearing"}}
    if study not in allowed or any(t.name not in allowed[study] for t in tasks):
        raise ValueError("Individual design requires a supported single simulation task")
    n=d.get("n",100)
    if type(n) is not int or not 40<=n<=100000 or (study in ("P01","P08") and n%4) or (study=="P04" and (n<100 or n%2)):
        raise ValueError("Invalid N; factorial designs require multiples of four")
    def bounded(k,lo,hi):
        v=d[k]
        if not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError("Invalid "+k)
        return v
    def category(k,choices):
        if d[k] not in choices:raise ValueError("Invalid "+k)
        return d[k]
    if study=="P01":
        args=["--design",n,bounded("effect1",-2,2),bounded("effect2",-2,2),category("profile",("equal","heterogeneous"))]
    elif study=="P03":
        args=["--effect",bounded("effect",0,.6)]
    elif study=="P04":
        args=["--design",n,bounded("effect",-.6,.6),category("noise",(.5,.9,1.4)),
              category("mechanism",("baseline_mar","status_dependent","outcome_dependent","composite_mar"))]
    elif study=="P05":
        args=["--loading",bounded("loading",.3,.9),"--missing",bounded("missing",0,.3)]
        if d.get("skew"):args.append("--skew")
    elif study=="P06":
        args=["--design",n,bounded("effect",-.6,.6),bounded("missing",0,.9),
              category("mechanism",("mcar","mar","mnar"))]
    elif study=="P07":
        args=["--design",n,bounded("prevalence",.01,.99),bounded("effect",-2,2),
              bounded("missing",0,.95),category("mechanism",("mcar","mar","mnar","confounded"))]
    else:
        args=["--design",n,bounded("authority",-2,2),bounded("interaction",-2,2),
              category("mechanism",("mcar","mar","mnar")),"--loss",bounded("missing",0,.95)]
    out=[]
    for t in tasks:
        a=list(t.args)
        if study=="P08":
            if "--nonadherence" in a:a[a.index("--nonadherence")+1]=str(bounded("nonadherence",0,.95))
            else:a.extend(["--nonadherence",str(bounded("nonadherence",0,.95))])
        out.append(t if t.deps else replace(t,args=tuple(a+list(map(str,args)))))
    return out

def decimal(label,lo,hi):
    while True:
        try:
            v=float(input(f"{label} [{lo}..{hi}]: ").replace(",","."))
            if math.isfinite(v) and lo<=v<=hi:return v
        except ValueError:pass
        print("Nieprawidlowa wartosc.")

def ask_design(study,pattern):
    supported=(study,pattern) in {("P01","cp-joint"),("P04","joint"),("P06","bounded"),("P07","primary"),("P08","factorial"),("P08","nonhearing")} or (study=="P03" and pattern.startswith("mi-")) or (study=="P05" and pattern.startswith("structure/"))
    if not supported:return None
    if input("Zmienic siatke na jeden wlasny scenariusz? [t/N]: ").strip().lower() not in ("t","tak","y","yes"):
        return None
    if study=="P03":return {"effect":decimal("Korelacja czastkowa",0,.6)}
    if study=="P05":return {"loading":decimal("Ladunek czynnikowy",.3,.9),"missing":decimal("Frakcja MCAR",0,.3),"skew":bool(integer("Skosnosc: 0=nie, 1=tak",0,1))}
    divisor=4 if study in ("P01","P08") else 2 if study=="P04" else 1
    minimum=100 if study=="P04" else 40
    n=integer("Liczebnosc N",minimum,100000)
    while n%divisor:n=integer(f"N musi byc wielokrotnoscia {divisor}",minimum,100000)
    d={"n":n}
    if study=="P01":
        d.update(effect1=decimal("Efekt prosty 1",-2,2),effect2=decimal("Efekt prosty 2",-2,2),
                 profile=("equal","heterogeneous")[integer("Profil: 1=equal, 2=heterogeneous",1,2)-1])
    elif study=="P04":
        choices=("baseline_mar","status_dependent","outcome_dependent","composite_mar")
        d.update(effect=decimal("Interakcja latentna",-.6,.6),noise=(.5,.9,1.4)[integer("Szum: 1=.5, 2=.9, 3=1.4",1,3)-1],mechanism=choices[integer("Mechanizm: 1=baseline, 2=status, 3=outcome, 4=composite",1,4)-1])
    else:
        choices=("mcar","mar","mnar","confounded") if study=="P07" else ("mcar","mar","mnar")
        d["mechanism"]=choices[integer("Mechanizm: "+", ".join(f"{i+1}={x}" for i,x in enumerate(choices)),1,len(choices))-1]
        d["missing"]=decimal("Frakcja brakow",0,.9 if study=="P06" else .95)
        if study=="P06":d.update(effect=decimal("Efekt latentny",-.6,.6))
        elif study=="P07":
            d.update(prevalence=decimal("Czestosc ekspozycji",.01,.99),effect=decimal("Efekt latentny",-2,2))
        else:
            d.update(authority=decimal("Efekt authority",-2,2),interaction=decimal("Interakcja",-2,2),
                     nonadherence=decimal("Frakcja nieprzestrzegania przydzialu",0,.95))
    return d

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
        design=ask_design(study,pattern)
        options={}
        while True:
            for k,(lo,hi,default) in FIELDS[study].items():
                options[k]=integer(LABELS[k],lo,hi,default)
            try:
                configured=build(study,reps,seed,options,pattern,design)
                break
            except ValueError as exc:
                print(exc)
        config={"study":study,"reps":reps,"seed":seed,"options":options,"pattern":pattern,
                "jobs":jobs,"threads":threads,"design":design}
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
