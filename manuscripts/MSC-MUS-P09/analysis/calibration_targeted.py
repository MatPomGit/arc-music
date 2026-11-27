"""Targeted high-precision calibration following the adverse P09 screening."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from calibration import cell, generate, proportion
from calibration_extended import summary
from missingness import sensitivity_endpoint

SEED = 20261129
METHODS = ("ipw", "shift_0/0")
MECHANISMS = ("MAR", "MNAR")


def hc3(reps=2000):
    grid = list(itertools.product((434,588), MECHANISMS, ("null","alternative")))
    seeds = np.random.SeedSequence([SEED,0]).spawn(len(grid))
    return dict(synthetic=True, seed=SEED, reps_per_cell=reps,
                cells=[cell(s,n,"heteroskedastic",m,e,reps)
                       for s,(n,m,e) in zip(seeds,grid)])


def shard(mechanism, index, count=100, draws=999):
    if mechanism not in MECHANISMS or not 0 <= index < 10 or min(count,draws)<2:
        raise ValueError("Invalid shard configuration")
    rows = []
    for i in range(count):
        # Independent streams for each outer dataset, including across shards.
        outer = index*count+i
        s = np.random.SeedSequence([SEED,1,MECHANISMS.index(mechanism),outer])
        data_seed, boot_seed = s.spawn(2)
        d = generate(np.random.default_rng(data_seed),588,"heteroskedastic",mechanism,"null")
        d["status"] = "defined"
        report = sensitivity_endpoint(d,"understanding2","status",draws,boot_seed)
        estimates = report.get("estimates",{})
        shifts = [v["contrast"] for k,v in estimates.items() if k.startswith("shift_")]
        diagnostics = report.get("response_diagnostics")
        rows.append(dict(index=outer, estimates={k:estimates[k] for k in METHODS if k in estimates},
                         positivity_warning=None if diagnostics is None else any(x["positivity_warning"] for x in diagnostics),
                         shift_envelope=None if len(shifts)!=25 else min(shifts)<=0<=max(shifts)))
    return dict(schema_version=1, synthetic=True, seed=SEED, mechanism=mechanism,
                shard=index,count=count,draws=draws,profile="heteroskedastic",effect="null",
                hypothesis="H1",n=588,rows=rows)


def aggregate(parts, *, count=100, draws=999):
    expected = {(m,i) for m in MECHANISMS for i in range(10)}
    seen = set()
    grouped = {m:[] for m in MECHANISMS}
    for p in parts:
        key = (p["mechanism"],p["shard"])
        if key not in expected or key in seen:
            raise ValueError("Unexpected or duplicate shard")
        seen.add(key)
        fixed = dict(schema_version=1, synthetic=True, seed=SEED,count=count,draws=draws,
                     profile="heteroskedastic",effect="null",hypothesis="H1",n=588)
        if any(p.get(k)!=v for k,v in fixed.items()):
            raise ValueError("Shard metadata mismatch")
        if sorted(r["index"] for r in p["rows"]) != list(range(key[1]*count,(key[1]+1)*count)):
            raise ValueError("Incomplete or duplicate outer replicates")
        for row in p["rows"]:
            for name,value in row["estimates"].items():
                if name not in METHODS or value["successful"]+value["failed"]!=draws:
                    raise ValueError("Invalid inner bootstrap accounting")
        grouped[key[0]].extend(p["rows"])
    if seen != expected:
        raise ValueError("Missing shards")
    result = {}
    for m,rows in grouped.items():
        result[m] = dict(methods={k:summary([r["estimates"][k] for r in rows if k in r["estimates"]],0.,len(rows))
                                  for k in METHODS},
                         positivity_warning=proportion([r["positivity_warning"] for r in rows if r["positivity_warning"] is not None]),
                         shift_envelope_contains_truth=proportion([r["shift_envelope"] for r in rows if r["shift_envelope"] is not None]))
    return dict(synthetic=True,seed=SEED,outer_per_cell=10*count,draws=draws,
                requested_bootstrap_draws=20*count*draws,
                note="H1 null only; MNAR coverage is a stress diagnostic, not identified nominal coverage.",
                scenarios=result)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    h=sub.add_parser("hc3"); h.add_argument("--reps",type=int,default=2000)
    s=sub.add_parser("shard"); s.add_argument("mechanism",choices=MECHANISMS); s.add_argument("index",type=int)
    s.add_argument("--count",type=int,default=100); s.add_argument("--draws",type=int,default=999)
    a=sub.add_parser("aggregate"); a.add_argument("directory",type=Path)
    args=p.parse_args()
    if args.command=="hc3":
        result=hc3(args.reps)
    elif args.command=="shard":
        result=shard(args.mechanism,args.index,args.count,args.draws)
    else:
        result=aggregate([json.loads(f.read_text()) for f in args.directory.rglob("shard.json")])
    print(json.dumps(result,indent=2,allow_nan=False))
