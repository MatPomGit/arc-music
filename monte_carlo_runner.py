"""Resumable local synthetic Monte Carlo runner; no participant data or network services."""
import argparse
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from contextlib import contextmanager
from dataclasses import dataclass
import fnmatch
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import runpy
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
STUDIES=tuple(f"P{i:02}" for i in range(1,10))
PROFILES=("smoke","pilot","full")
VERSION="1.2.0"

@dataclass(frozen=True)
class Job:
    name:str
    script:str
    args:tuple
    deps:tuple=()
    r:bool=False

def job(name,script,*args,deps=(),r=False):
    return Job(name,script,tuple(map(str,args)),tuple(deps),r)

def directory(study):
    return ROOT/"manuscripts"/("MSC-MUS-"+study)

def load_plan(study,profile):
    tasks=runpy.run_path(str(directory(study)/"monte_carlo.py"))["plan"](profile)
    names=[t.name for t in tasks]
    if len(set(names))!=len(names):raise ValueError("Duplicate task names")
    known=set(names)
    for t in tasks:
        if not re.fullmatch(r"[a-z0-9_-]+(?:/[a-z0-9_-]+)*",t.name):
            raise ValueError("Unsafe task name")
        if not re.fullmatch(r"[a-zA-Z0-9_]+\.py",t.script) or not (directory(study)/"analysis"/t.script).is_file():
            raise ValueError("Missing or unsafe script: "+t.script)
        if not set(t.deps)<=known or t.name in t.deps:
            raise ValueError("Invalid dependencies: "+t.name)
    pending=set(names);seen=set()
    while pending:
        ready={t.name for t in tasks if t.name in pending and set(t.deps)<=seen}
        if not ready:raise ValueError("Dependency cycle")
        seen.update(ready);pending-=ready
    return tasks

def selected(tasks,pattern):
    keep={t.name for t in tasks if fnmatch.fnmatchcase(t.name,pattern)}
    if not keep and tasks:raise ValueError("No matching tasks: "+pattern)
    by={t.name:t for t in tasks}
    pending=list(keep)
    while pending:
        for dep in by[pending.pop()].deps:
            if dep not in keep:keep.add(dep);pending.append(dep)
    return [t for t in tasks if t.name in keep]

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):digest.update(block)
    return digest.hexdigest()

def json_text(x):
    return json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+"\n"

def atomic_json(path,x):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".tmp")
    tmp.write_text(json_text(x),encoding="utf-8")
    os.replace(tmp,path)

def strict_json(path):
    def invalid(s):raise ValueError("Nonfinite JSON token: "+s)
    with path.open(encoding="utf-8") as f:
        value=json.load(f,parse_constant=invalid)
    if not isinstance(value,(dict,list)) or not value:
        raise ValueError("Expected nonempty simulation JSON object or array")
    return value

def output(out,name):return out/(name+".json")
# Metadata must never match simulation aggregators' shard-*.json glob.
def stamp(out,name):return out/".metadata"/(name+".json")

def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()

def source_hash(study):
    paths=[ROOT/"monte_carlo_runner.py",ROOT/"monte_carlo_results.py",ROOT/"monte_carlo_custom.py",directory(study)/"monte_carlo.py"]
    tracked=git("ls-files","-z","--",str(directory(study).relative_to(ROOT))).split("\0")
    paths.extend(ROOT/p for p in tracked if p and Path(p).suffix in (".py",".R",".r",".csv",".txt",".json"))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}

def environment(tasks,study,threads):
    requirements={"P01":("numpy","scipy"),"P03":("numpy","scipy","pandas","statsmodels"),
                  "P04":("numpy","scipy"),"P05":("numpy","scipy")}
    versions={}
    for package in requirements.get(study,("numpy","scipy","pandas")):
        try:versions[package]=metadata.version(package)
        except metadata.PackageNotFoundError:raise ValueError("Missing Python dependency: "+package)
    env={"python":sys.version,"executable":str(Path(sys.executable).resolve()),
         "platform":platform.platform(),"machine":platform.machine(),
         "packages":versions,"threads_per_job":threads}
    # Capture actual BLAS/backend and machine configuration, not just versions.
    config=subprocess.run([sys.executable,"-c","import numpy as np;np.show_config()"],
                          capture_output=True,text=True,check=True)
    env["numpy_config"]=config.stdout
    if any(t.r for t in tasks):
        result=subprocess.run(["Rscript","-e",'library(lavaan);library(semTools);sessionInfo()'],
                              capture_output=True,text=True,check=True)
        env["r_session"]=result.stdout
    return env

@contextmanager
def lock(out):
    out.mkdir(parents=True,exist_ok=True)
    path=out/".run.lock"
    try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise ValueError("Run locked: "+str(path)+"; remove only after verifying no process is active")
    try:
        with os.fdopen(fd,"w") as f:f.write(str(os.getpid())+"\n")
        yield
    finally:path.unlink(missing_ok=True)

def signature(task,ctx,out):
    return {"context":ctx,"script":task.script,"args":list(task.args),
            "dependencies":{d:sha(output(out,d)) for d in task.deps}}

def reusable(task,ctx,out):
    try:
        m=strict_json(stamp(out,task.name));o=output(out,task.name)
        return m["signature"]==signature(task,ctx,out) and m["sha256"]==sha(o) and bool(strict_json(o))
    except (OSError,ValueError,KeyError,TypeError):return False

def execute(task,ctx,out,study,threads):
    if reusable(task,ctx,out):return "REUSED"
    target=output(out,task.name);target.parent.mkdir(parents=True,exist_ok=True)
    stamp(out,task.name).unlink(missing_ok=True)
    target.unlink(missing_ok=True)
    args=[a.replace("@OUT@",str(out)) for a in task.args]
    cmd=[sys.executable,str(directory(study)/"analysis"/task.script),*args]
    env=os.environ.copy()
    for name in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS","BLIS_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
        env[name]=str(threads)
    temp=target.with_suffix(".partial")
    log=target.with_suffix(".stderr.log")
    started=time.time()
    with temp.open("wb") as stdout,log.open("wb") as stderr:
        code=subprocess.run(cmd,cwd=directory(study)/"analysis",env=env,stdout=stdout,stderr=stderr).returncode
    if code:raise RuntimeError(f"Exit {code}; inspect {log} and {temp}")
    strict_json(temp)
    if git("rev-parse","HEAD")!=ctx["head"] or source_hash(study)!=ctx["sources"]:
        raise RuntimeError("Source changed during execution; result not accepted")
    os.replace(temp,target)
    atomic_json(stamp(out,task.name),{"signature":signature(task,ctx,out),"sha256":sha(target),
               "seconds":time.time()-started,"status":"EXECUTED","synthetic":True,
               "confirmatory_authorized":False})
    return "EXECUTED"

def schedule(tasks,worker,jobs):
    state={};remaining={t.name:t for t in tasks};active={}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        while remaining or active:
            while True:
                blocked=[t for t in remaining.values() if any(state.get(d) in ("FAILED","BLOCKED") for d in t.deps)]
                if not blocked:break
                for t in blocked:
                    state[t.name]="BLOCKED";remaining.pop(t.name)
                    print(f"[{len(state)}/{len(tasks)}] {t.name} BLOCKED",flush=True)
            ready=[t for t in remaining.values() if all(state.get(d) in ("EXECUTED","REUSED") for d in t.deps)]
            for t in ready[:max(0,jobs-len(active))]:
                active[pool.submit(worker,t)]=t;remaining.pop(t.name)
            if not active:
                if remaining:raise RuntimeError("Unresolved dependencies")
                break
            done,_=wait(active,return_when=FIRST_COMPLETED)
            for future in done:
                t=active.pop(future)
                try:state[t.name]=future.result()
                except Exception as exc:
                    state[t.name]="FAILED"
                    print(t.name,str(exc),file=sys.stderr,flush=True)
                print(f"[{len(state)}/{len(tasks)}] {t.name} {state[t.name]}",flush=True)
    return state

def run_study(study,profile,pattern,jobs,threads,base,run_id,custom=None):
    tasks=selected(load_plan(study,profile),pattern) if custom is None else custom
    if not tasks:
        print(study+": NOT_APPLICABLE (qualitative design)")
        return True
    # Deliberately refuse dirty source trees; run only reviewed tracked code.
    if git("status","--porcelain","--untracked-files=all","--","monte_carlo_runner.py","monte_carlo_results.py","monte_carlo_custom.py",str(directory(study).relative_to(ROOT))):
        raise ValueError("Commit or use a clean checkout of the reviewed source first")
    from monte_carlo_results import describe_plan, export_plots
    describe_plan(study,profile,tasks)
    head=git("rev-parse","HEAD")
    out=(base/head/study/profile/run_id).resolve()
    ctx={"runner_version":VERSION,"head":head,"study":study,"profile":profile,
         "sources":source_hash(study),"environment":environment(tasks,study,threads)}
    with lock(out):
        context=out/"context.json"
        if context.exists() and strict_json(context)!=ctx:
            raise ValueError("Run context differs; choose another --run-id: "+str(out))
        atomic_json(context,ctx)
        state=schedule(tasks,lambda t:execute(t,ctx,out,study,threads),jobs)
        ok=all(v in ("EXECUTED","REUSED") for v in state.values())
        atomic_json(out/"run-summary.json",{"context":ctx,"tasks":state,
            "synthetic":True,"confirmatory_authorized":False,"all_requested_executed":ok})
        plot_dir=directory(study)/"results"/head/profile/run_id
        count=export_plots(tasks,state,out,plot_dir,study,profile)
        print(f"Plots: {count}; {plot_dir}",flush=True)
        return ok and count>0

def main(default_study="all"):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",choices=("all",*STUDIES),default=default_study)
    p.add_argument("--profile",choices=PROFILES,default="smoke")
    p.add_argument("--task",default="*",help="Glob of task names; required dependencies included")
    p.add_argument("--jobs",type=int,default=1)
    p.add_argument("--threads",type=int,default=1)
    p.add_argument("--run-id",default="local",help="Separate environment/run namespace")
    p.add_argument("--list",action="store_true",help="List exact commands, no computation or dependency installation")
    p.add_argument("--summary",action="store_true",help="Show planned outer replications without running")
    p.add_argument("--custom",action="store_true",help="Interactive custom simulation configuration")
    a=p.parse_args()
    if min(a.jobs,a.threads)<1 or not re.fullmatch("[a-zA-Z0-9_-]+",a.run_id):
        p.error("Positive jobs/threads and simple run ID required")
    if a.jobs*a.threads>(os.cpu_count() or 1):
        p.error("Requested workers × threads exceeds available logical CPUs")
    chosen=STUDIES if a.study=="all" else (a.study,)
    if a.custom:
        if a.study=="all" or a.summary or a.list:
            p.error("Custom mode requires a single study and no list/summary flags")
        from monte_carlo_custom import interactive
        try:
            raise SystemExit(interactive(a.study))
        except (ValueError,OSError,subprocess.SubprocessError) as exc:
            print(str(exc),file=sys.stderr)
            raise SystemExit(1)
    if a.summary:
        from monte_carlo_results import describe_plan
        for study in chosen:
            describe_plan(study,a.profile,selected(load_plan(study,a.profile),a.task))
        return
    if a.list:
        for study in chosen:
            tasks=selected(load_plan(study,a.profile),a.task)
            print(study,json_text([{"task":t.name,"command":[t.script,*t.args],"depends_on":list(t.deps),"requires_r":t.r} for t in tasks]))
            if not tasks:print("NOT_APPLICABLE: qualitative design")
        return
    base=ROOT/"build"/"monte-carlo"
    success=True
    for study in chosen:
        try:success=run_study(study,a.profile,a.task,a.jobs,a.threads,base,a.run_id) and success
        except (ValueError,OSError,subprocess.SubprocessError) as exc:
            print(study,str(exc),file=sys.stderr);success=False
    raise SystemExit(0 if success else 1)

if __name__=="__main__":main()
