"""Exact synthetic input serialization and replay, independent of BLAS draws."""
import hashlib
import io
import json
from pathlib import Path
import numpy as np

VERSION="p05-reference-inputs-v1"

def encode(x,factors,items):
    x=np.asarray(x)
    if x.ndim!=2 or x.shape[1]!=factors*items or x.shape[0]<30:
        raise ValueError("Invalid reference input shape")
    if not np.isfinite(x).all() or not np.isin(x,np.arange(5)).all():
        raise ValueError("Synthetic ordinal input must be complete, integer 0..4")
    stream=io.StringIO()
    np.savetxt(stream,x,fmt="%d",delimiter=",",header=",".join(f"item{i+1}" for i in range(x.shape[1])),comments="",newline="\n")
    return stream.getvalue().encode("ascii")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_input(folder,x,factors,items,index):
    path=Path(folder)/f"case-{index:02d}.csv"
    data=encode(x,factors,items)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    return path.name,digest(data)

def write_manifest(folder,rows):
    entries=[]
    for i,row in enumerate(rows):
        meta={k:row[k] for k in ("n","factors","items_per_factor","loading","rho","skew","seed")}
        meta.update(file=f"case-{i:02d}.csv",input_sha256=row["input_sha256"])
        if "draw" in row:meta["draw"]=row["draw"]
        entries.append(meta)
    (Path(folder)/"manifest.json").write_text(json.dumps({"schema":VERSION,"synthetic":True,"cases":entries},indent=2)+"\n",encoding="utf-8")

def replay(folder):
    folder=Path(folder)
    manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema")!=VERSION or manifest.get("synthetic") is not True:
        raise ValueError("Unknown or non-synthetic archive")
    rows=manifest["cases"]
    if not rows:raise ValueError("Empty reference input archive")
    expected={"manifest.json",*(f"case-{i:02d}.csv" for i in range(len(rows)))}
    if {p.name for p in folder.iterdir()}!=expected:
        raise ValueError("Unexpected or missing input archive files")
    for i,meta in enumerate(rows):
        name=f"case-{i:02d}.csv"
        if meta["file"]!=name:raise ValueError("Unexpected reference input name")
        path=folder/name
        if path.is_symlink():raise ValueError("Linked reference input")
        data=path.read_bytes()
        if digest(data)!=meta["input_sha256"]:raise ValueError("Reference input digest mismatch")
        x=np.loadtxt(io.BytesIO(data),delimiter=",",skiprows=1,ndmin=2)
        if x.shape!=(meta["n"],meta["factors"]*meta["items_per_factor"]) or encode(x,meta["factors"],meta["items_per_factor"])!=data:
            raise ValueError("Noncanonical reference input")
        yield meta,x
