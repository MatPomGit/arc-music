"""Offline diagnostic SVG figures and outer replication accounting."""
from collections import defaultdict
from html import escape
import json
import math
from pathlib import Path

# Full/pilot cell counts from the corresponding production simulation grids.
CELLS={"P01":{"cp-joint":96},"P03":{},"P04":{"joint":48},
       "P06":{"cluster":27,"bounded":18,"missing":12,"bootstrap":6},
       "P07":{"primary":44,"secondary":72},
       "P08":{"factorial":36,"nonhearing":36,"bootstrap":2}}
SMOKE={"P04":{"joint":3},"P07":{"primary":3,"secondary":4},"P08":{"factorial":2,"nonhearing":2}}

def planned_reps(study,profile,task):
    args=task.args
    if task.deps:
        return 0
    if study=="P09" and args and args[0]=="shard":
        return int(args[3])
    if "--reps" not in args:
        return 0
    reps=int(args[args.index("--reps")+1])
    if "--design" in args or (study=="P03" and "--effect" in args):
        return reps
    if study=="P03":
        return reps*2
    cells=SMOKE.get(study,{}).get(task.name) if profile=="smoke" else None
    if cells is None:
        cells=CELLS.get(study,{}).get(task.name,1)
    return reps*cells

def describe_plan(study,profile,tasks):
    if not tasks:
        print(study+": NOT_APPLICABLE (qualitative design)")
        return
    counts=[planned_reps(study,profile,t) for t in tasks]
    reps=sorted({int(t.args[t.args.index("--reps")+1]) for t in tasks if "--reps" in t.args and "/shard-" not in t.name})
    # Sharded runs display complete scenario denominators, not shard sizes.
    reps.extend(sorted({int(t.args[t.args.index("--expected")+1]) for t in tasks if "--expected" in t.args}))
    print(f"{study} / {profile}: {len(tasks)} computational jobs (including aggregation)")
    print("Outer replications per scenario:",", ".join(map(str,sorted(set(reps)))) or "see task list")
    if all(c is not None for c in counts):
        qualifier=" (EFA and independent CFA datasets counted as one paired replication)" if study=="P05" else ""
        print(f"Planned outer scenario replications: {sum(counts):,}"+qualifier)
    else:
        print("Exact total not available for this smoke grid.")
    print("Bootstrap draws and permutations are not counted as independent outer replications.",flush=True)

SCENARIO_KEYS=("n","sizes","structure","scenario","mechanism","profile","e","effect","partial_r_input",
               "latent_interaction","noise","beta","prevalence","missing","latent_beta","latent_authority",
               "cell","targets","loading","item_mcar")
SKIP={"records","references","reference","generating_covariance","environment","failure_reasons",
      "unavailable_reasons","status_counts","paired_test_decisions","context","exact_rounded_mixed_mar_retention"}
def metric(key):
    k=key.lower()
    if "mcse" in k or "interval" in k or "width" in k or k.endswith("_se") or k.endswith("_count"):
        return k=="rmse"
    return (k in {"joint","psi_positive","bias","rmse","power","type_i","fwer","valid_fraction",
                  "availability","attainment","operational_rate","conditional_rate","all_three_reject",
                  "efa_correct_count","efa_joint_recovery","paired_identical_rejection_sets"} or
            any(x in k for x in ("coverage","rejection","reject","available_fraction")))

def collect(value, label, prefix=(), groups=None):
    if groups is None:
        groups=defaultdict(list)
    if isinstance(value,dict):
        extra=", ".join(f"{k}={value[k]}" for k in SCENARIO_KEYS if k in value)
        if extra:
            label=f"{label} | {extra}"
        for k,v in value.items():
            if k in SKIP or k in SCENARIO_KEYS:
                continue
            path=prefix+(k,)
            if metric(k):
                number=v.get("rate") if isinstance(v,dict) else v
                values=number if isinstance(number,list) else [number]
                for i,x in enumerate(values):
                    if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x):
                        suffix=f" [{i+1}]" if isinstance(number,list) else ""
                        groups[" / ".join(path)+suffix].append((label,float(x)))
            if isinstance(v,(list,dict)) and not (metric(k) and isinstance(v,dict) and "rate" in v):
                collect(v,label,path,groups)
    elif isinstance(value,list):
        for i,v in enumerate(value):
            if isinstance(v,(dict,list)):
                collect(v,f"{label} | row {i+1}",prefix,groups)
    return groups

def summary_svg(study,profile,groups,complete):
    """One multi-panel figure; independent scales, no pooling across estimands."""
    width=1600
    body=[]
    y=112
    families=defaultdict(dict)
    for (family,name),rows in sorted(groups.items()):
        families[family][name]=rows
    for family,metrics in families.items():
        labels=list(dict.fromkeys(label for rows in metrics.values() for label,_ in rows))
        names=list(metrics)
        # Each panel has its own metric scale. All panels share scenario order.
        for start in range(0,len(names),5):
            cols=names[start:start+5]
            lookup={}
            bounds={}
            for name in cols:
                lookup[name]={}
                for label,value in metrics[name]:
                    if label in lookup[name]:
                        raise ValueError("Duplicate scenario/metric: "+label+" / "+name)
                    lookup[name][label]=value
                values=list(lookup[name].values())
                key=name.lower().split(" / ")[-1]
                if "bias" in key:
                    lim=max(abs(v) for v in values) or 1.
                    bounds[name]=(-lim,lim)
                elif all(0<=v<=1 for v in values) and "rmse" not in key and "count" not in key:
                    bounds[name]=(0.,1.)
                else:
                    bounds[name]=(min(0.,min(values)),max(0.,max(values)) or 1.)
            body.append(f'<text x="20" y="{y}" font-size="18" font-weight="bold">{escape(family)} | metrics {start+1}-{start+len(cols)} / {len(names)}</text>')
            y+=16
            for j,name in enumerate(cols):
                x=660+j*184
                lo,hi=bounds[name]
                short=name if len(name)<=24 else name[-23:]
                body.append(f'<text x="{x+90}" y="{y+18}" text-anchor="middle" font-size="12"><title>{escape(name)}</title>{escape(short)}</text>')
                body.append(f'<text x="{x+90}" y="{y+34}" text-anchor="middle" font-size="11">{lo:.3g} to {hi:.3g}</text>')
            y+=44
            for label in labels:
                short=label if len(label)<=92 else label[:89]+"..."
                body.append(f'<text x="20" y="{y+16}" font-size="11"><title>{escape(label)}</title>{escape(short)}</text>')
                for j,name in enumerate(cols):
                    x=660+j*184
                    value=lookup[name].get(label)
                    lo,hi=bounds[name]
                    body.append(f'<rect x="{x}" y="{y}" width="180" height="22" fill="#f1f3f5"/>')
                    if value is not None:
                        scale=lambda v:x+4+126*(v-lo)/(hi-lo) if hi>lo else x+4
                        a,b=sorted((scale(0),scale(value)))
                        body.append(f'<rect x="{a:.2f}" y="{y+4}" width="{max(1,b-a):.2f}" height="14" fill="#3779ac"><title>{escape(label+" / "+name)}: {value:.8g}</title></rect>')
                        shown=f"{value:.4g}"
                    else:
                        shown="NA"
                    body.append(f'<text x="{x+176}" y="{y+16}" text-anchor="end" font-size="11">{shown}</text>')
                y+=24
            y+=30
    status="COMPLETE" if complete else "PARTIAL - failed or blocked tasks excluded"
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{y+20}" viewBox="0 0 {width} {y+20}" font-family="sans-serif">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="20" y="34" font-size="24" font-weight="bold">{escape(study+" / "+profile+" : Monte Carlo summary")}</text>',
        f'<text x="20" y="60" font-size="15">{status}</text>',
        '<text x="20" y="83" font-size="13">Rows: scenarios. Columns: metrics with separate numeric scales. NA: unavailable. Synthetic results.</text>',
        *body,'</svg>'])

def export_plots(tasks,state,out,dest,study,profile):
    dest.mkdir(parents=True,exist_ok=True)
    index=dest/"plot-index.json"
    old_files=set()
    if index.exists():
        for entry in json.loads(index.read_text(encoding="utf-8")).get("plots",[]):
            name=entry["file"]
            if Path(name).name==name and name.startswith("mc-") and name.endswith(".svg"):
                old_files.add(name)
    groups=defaultdict(list)
    for task in tasks:
        if state.get(task.name) not in {"EXECUTED","REUSED"} or "/shard-" in task.name:
            continue
        payload=json.loads((out/(task.name+".json")).read_text(encoding="utf-8"))
        family=task.name.split("/")[0]
        for metric_name,rows in collect(payload,task.name).items():
            groups[(family,metric_name)].extend(rows)
    complete=all(state.get(t.name) in {"EXECUTED","REUSED"} for t in tasks)
    filename="mc-summary.svg"
    entries=[]
    if groups:
        temp=dest/(filename+".tmp")
        temp.write_text(summary_svg(study,profile,groups,complete),encoding="utf-8")
        temp.replace(dest/filename)
        entries=[{"file":filename,"panels":[{"family":family,"metric":name,
                  "rows":[{"scenario":label,"value":v} for label,v in rows]}
                  for (family,name),rows in sorted(groups.items())]}]
    temp=index.with_suffix(".tmp")
    temp.write_text(json.dumps({"synthetic":True,"profile":profile,"plots":entries,
                               "complete":complete},indent=2,ensure_ascii=False),encoding="utf-8")
    temp.replace(index)
    for name in old_files-({filename} if groups else set()):
        (dest/name).unlink(missing_ok=True)
    return len(entries)
