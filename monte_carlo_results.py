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
    if "--design" in args:
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

def svg(title,rows):
    # Horizontal dot chart with explicit numeric axis; no implicit zero or
    # pooling of distinct conditional and operational metrics.
    width=1250; left=720; right=1180; top=90; step=24
    height=top+len(rows)*step+65
    vals=[v for _,v in rows]
    low=min(0.,min(vals)); high=max(0.,max(vals))
    if high==low: high=1.
    scale=lambda v:left+(v-low)/(high-low)*(right-left)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="20" y="30" font-size="17" font-family="sans-serif">{escape(title)}</text>',
           '<text x="20" y="55" font-size="13" fill="#555" font-family="sans-serif">Synthetic Monte Carlo diagnostics; scenario rows, not empirical observations.</text>']
    for i in range(5):
        val=low+(high-low)*i/4; x=scale(val)
        parts.append(f'<path d="M{x:.2f} {top-12} V{height-50}" stroke="#ddd"/>')
        parts.append(f'<text x="{x:.2f}" y="{height-25}" text-anchor="middle" font-size="12">{val:.3g}</text>')
    for i,(label,v) in enumerate(rows):
        y=top+i*step
        short=label if len(label)<=100 else label[:97]+"..."
        parts.append(f'<text x="15" y="{y+4}" font-size="11" font-family="sans-serif"><title>{escape(label)}</title>{escape(short)}</text>')
        parts.append(f'<circle cx="{scale(v):.2f}" cy="{y}" r="4" fill="#245b85"><title>{v:.8g}</title></circle>')
        parts.append(f'<text x="1240" y="{y+4}" text-anchor="end" font-size="11">{v:.4g}</text>')
    parts.append('</svg>')
    return "\n".join(parts)

def export_plots(tasks,state,out,dest,study,profile):
    dest.mkdir(parents=True,exist_ok=True)
    # A resumed run may have fewer selected outputs. Remove only our own
    # previously indexed plot files, never user-created figures.
    index=dest/"plot-index.json"
    if index.exists():
        for entry in json.loads(index.read_text(encoding="utf-8")).get("plots",[]):
            name=entry["file"]
            if Path(name).name==name and name.startswith("mc-") and name.endswith(".svg"):
                (dest/name).unlink(missing_ok=True)
    groups=defaultdict(list)
    for task in tasks:
        if state.get(task.name) not in {"EXECUTED","REUSED"} or "/shard-" in task.name:
            continue
        payload=json.loads((out/(task.name+".json")).read_text(encoding="utf-8"))
        # Group by job family rather than combining unrelated estimands.
        family=task.name.split("/")[0]
        for metric_name,rows in collect(payload,task.name).items():
            groups[(family,metric_name)].extend(rows)
    entries=[]
    for (family,name),rows in sorted(groups.items()):
        for start in range(0,len(rows),30):
            filename=f"mc-{len(entries)+1:04}.svg"
            chunk=rows[start:start+30]
            (dest/filename).write_text(svg(f"{study} {profile}: {family} / {name}",chunk),encoding="utf-8")
            entries.append({"file":filename,"family":family,"metric":name,"rows":[{"scenario":s,"value":v} for s,v in chunk]})
    index.write_text(json.dumps({"synthetic":True,"profile":profile,"plots":entries,
                                 "complete":all(state.get(t.name) in {"EXECUTED","REUSED"} for t in tasks)},indent=2,ensure_ascii=False),encoding="utf-8")
    return len(entries)
