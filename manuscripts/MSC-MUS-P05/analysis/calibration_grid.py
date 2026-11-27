"""Sharded full-pool CFA calibration with deterministic per-replicate seeds.

Run only on synthetic data. No automatic decision from smoke samples.
Each scenario/shard is independently restartable, with immutable metadata.
"""
import argparse,json,hashlib,itertools
from pathlib import Path
import numpy as np
from recovery import simulate
from robust_cfa import robust_fit
from robust_calibration import wilson

def scenarios():
    result=[]
    for n,l,r,skew in itertools.product((250,400,500,650,800),(.60,.75),(.20,.50),(False,True)):
        result.append(dict(n=n,loading=l,rho=r,skew=skew,missing=0.,kind="core"))
    for n in (250,400,500,650,800):
        result.append(dict(n=n,loading=.40,rho=.80,skew=True,missing=0.,kind="stress"))
        for rate in (.02,.10,.20):
            result.append(dict(n=n,loading=.65,rho=.35,skew=True,missing=rate,kind="mcar_complete_case"))
    return [dict(id=i,**s) for i,s in enumerate(result)]

def diagnostic_scenarios():
    settings = [(400,.65,.35,False), (650,.65,.35,False),
                (500,.40,.80,True), (800,.40,.80,True),
                (800,.40,.35,True), (800,.65,.80,True)]
    return [dict(id=i,n=n,loading=l,rho=r,skew=skew,missing=0.,kind="diagnostic")
            for i,(n,l,r,skew) in enumerate(settings,100)]

def run(scenario,offset,count,seed=20261126):
    if offset<0 or count<1 or offset+count>2000:
        raise ValueError("replication range must lie within 0..1999")
    d=np.repeat(np.arange(7),5)
    truth=np.r_[np.full(35,scenario["loading"]),np.full(21,scenario["rho"])]
    records=[]
    for i in range(offset,offset+count):
        rng=np.random.default_rng(np.random.SeedSequence([seed,scenario["id"],i]))
        x=simulate(scenario["n"],7,5,scenario["loading"],scenario["rho"],
                   scenario["skew"],scenario["missing"],rng)
        x=x[np.isfinite(x).all(axis=1)]
        row={"replicate":i,"complete_n":len(x)}
        try:
            f=robust_fit(x,d)
            cover=(f.intervals[:,0]<=truth)&(truth<=f.intervals[:,1])
            row.update(status="proper",error=(f.parameters-truth).tolist(),
                       covered=cover.tolist(),reject=bool(f.p_value<.05))
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            row.update(status="failure",reason=str(exc))
        records.append(row)
    return dict(schema=1,scenario=scenario,seed=seed,records=records,
                label="SYNTHETIC DEVELOPMENT; estimator not validated WLSMV")

def aggregate(shards):
    if not shards:
        raise ValueError("no shards")
    ref=shards[0]
    if any(s["schema"]!=ref["schema"] or s["scenario"]!=ref["scenario"] or s["seed"]!=ref["seed"] for s in shards):
        raise ValueError("mixed scenario or seed")
    rows=sorted([row for s in shards for row in s["records"]],key=lambda r:r["replicate"])
    ids=[r["replicate"] for r in rows]
    if len(set(ids))!=len(ids) or not ids:
        raise ValueError("duplicate or empty replication records")
    good=[r for r in rows if r["status"]=="proper"]
    total=len(rows); proper=len(good)
    out={"scenario":ref["scenario"],"requested":total,"proper":proper,
         "proper_interval":wilson(proper,total),"mean_complete_n":float(np.mean([r["complete_n"] for r in rows])),
         "contiguous_from_zero":ids==list(range(total)),"decision":"not_calibrated"}
    out["failure_reasons"] = {}
    for r in rows:
        if r["status"] == "failure":
            reason = r.get("reason", "unspecified")
            out["failure_reasons"][reason] = out["failure_reasons"].get(reason, 0) + 1
    # Keep failed fits in the requested-replicate denominator.
    proper_rate = proper / total
    out["proper_mcse"] = float(np.sqrt(proper_rate*(1-proper_rate)/total))
    if good:
        errors=np.asarray([r["error"] for r in good]); covers=np.asarray([r["covered"] for r in good])
        if errors.shape!=(proper,56) or covers.shape!=errors.shape:
            raise ValueError("parameter dimensions disagree")
        coverage=covers.mean(axis=0)
        bias=errors.mean(axis=0)
        null_rejection = sum(r["reject"] for r in good)/proper
        out.update(max_abs_loading_bias=float(np.max(abs(bias[:35]))),
                   coverage_conditional=coverage.tolist(),coverage_unconditional=(covers.sum(axis=0)/total).tolist(),
                   coverage_intervals=[wilson(int(c),proper) for c in covers.sum(axis=0)],
                   bias=bias.tolist(),rmse=np.sqrt(np.mean(errors**2,axis=0)).tolist(),
                   coverage_mcse=np.sqrt(coverage*(1-coverage)/proper).tolist(),
                   null_rejection=null_rejection,
                   null_rejection_mcse=float(np.sqrt(null_rejection*(1-null_rejection)/proper)))
    # No automatic statistical acceptance: independent estimator validation,
    # EFA recovery, MI/MNAR and validity power are separate required gates.
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--list",action="store_true")
    p.add_argument("--diagnostic",action="store_true",help="Use the weak-structure diagnostic scenarios")
    p.add_argument("--scenario",type=int)
    p.add_argument("--offset",type=int,default=0)
    p.add_argument("--count",type=int,default=10)
    p.add_argument("--seed",type=int,default=20261126)
    p.add_argument("--out",type=Path)
    p.add_argument("--aggregate",nargs="+",type=Path)
    args=p.parse_args()
    grid = {s["id"]: s for s in (diagnostic_scenarios() if args.diagnostic else scenarios())}
    if args.list:
        result=list(grid.values())
    elif args.aggregate:
        result=aggregate([json.loads(f.read_text()) for f in args.aggregate])
    else:
        if args.scenario not in grid:
            p.error("valid scenario ID required")
        result=run(grid[args.scenario],args.offset,args.count,args.seed)
    payload=json.dumps(result,indent=2,allow_nan=False)+"\n"
    if args.out:
        with args.out.open("x",encoding="utf-8") as f:
            f.write(payload)
        print(hashlib.sha256(payload.encode()).hexdigest())
    else:
        print(payload,end="")
