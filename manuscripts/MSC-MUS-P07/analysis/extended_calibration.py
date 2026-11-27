"""P07 extended synthetic secondary screen and exact finite-window outcome bounds."""
import argparse, itertools, json, platform
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import scipy
from scipy.special import expit
from scipy.optimize import brentq
from inference import fit_arrays, holm


def observed(rng, risk, target):
    z=brentq(lambda z: expit(z+risk).mean()-target,-40,40)
    return rng.random(len(risk))>=expit(z+risk)


def generate(n, prev, effects, mechanism, rng):
    g=np.repeat(np.arange(n),21); day=np.tile(np.arange(1,22),n)
    u=rng.normal(size=n); prop=rng.normal(0,1.15,n)
    hour=rng.uniform(9,18,len(g))
    v=np.clip(np.rint(5+.7*u[g]+rng.normal(0,1.7,len(g))),0,10)
    a=np.clip(np.rint(5+rng.normal(0,1.8,len(g))),0,10)
    intent=np.clip(np.rint(4+.9*prop[g]+rng.normal(0,2,len(g))),0,10)
    logits=prop[g]+.25*(intent-4)-.15*(v-5)+.07*(hour-13.5)
    c=(rng.random(len(g))<expit(brentq(lambda z:expit(z+logits).mean()-prev,-40,40)+logits)).astype(int)
    x=np.column_stack([c,v,a,intent,day,hour]); desired=rng.integers(3,8,len(g)); dev0=np.abs(a-desired)
    person=rng.uniform(-.45,.45,n)[g]
    mu2=5+.20*(v-5)+.06*(a-5)+.06*(intent-5)+.01*(day-11)+.02*(hour-13.5)+person+effects[0]*c
    mu3=1.35+.10*(dev0-2)+.025*(a-5)+.02*(v-5)+.015*(intent-5)+.006*(day-11)+.01*(hour-13.5)+.25*person+effects[1]*c
    if np.any((mu2<=0)|(mu2>=10)|(mu3<=0)|(mu3>=3)):raise ValueError('Mean outside support')
    y2=rng.binomial(10,mu2/10); y3=rng.binomial(3,mu3/3)
    zero=np.zeros(len(g)); mcar=mechanism=='mcar'
    base=observed(rng,zero if mcar else .18*(v-5),.15)
    ex=observed(rng,zero if mcar else .20*(intent-5)+(.9*c if mechanism=='joint_mnar' else 0),.15)
    eligible=observed(rng,.3*(intent-4),.15); timely=rng.random(len(g))>=.10
    risk=.15*(5-v.reshape(n,21)[:,:-1])-.12*(intent.reshape(n,21)[:,:-1]-4)
    z=brentq(lambda z:np.mean(1-np.prod(1-expit(z+risk),axis=1))-.45,-40,40)
    retained=np.ones((n,21),bool);retained[:,1:]=np.cumprod(rng.random((n,20))>=expit(z+risk),axis=1).astype(bool)
    known=base&ex&eligible&timely&retained.ravel()
    r2=zero if mcar else .20*(v-5)+.3*c
    r3=zero if mcar else .20*(a-5)+.3*c
    if mechanism=='joint_mnar':
        r2=r2+.5*(y2-5)+.25*c*(y2-5);r3=r3+.6*(y3-1.35)+.35*c*(y3-1.35)
    return g, known, {'H2':(x,y2,observed(rng,r2,.15),np.full(len(g),10.)), 'H3':(np.column_stack([x,dev0]),y3,observed(rng,r3,.15),np.maximum(desired,10-desired))}


def outcome_bounds(g,x,y,seen,upper):
    """Sharp coefficient bounds on the fixed known-exposure switcher design."""
    _,g=np.unique(g,return_inverse=True); counts=np.bincount(g); exposed=np.bincount(g,weights=x[:,0]); keep=(exposed[g]>0)&(exposed[g]<counts[g])
    g,x,y,seen,upper=g[keep],x[keep],y[keep],seen[keep],upper[keep]
    _,g=np.unique(g,return_inverse=True);counts=np.bincount(g)
    if len(counts)<10:raise ValueError('Too few switchers')
    means=np.zeros((len(counts),x.shape[1]));np.add.at(means,g,x);w=x-means[g]/counts[g,None]
    if np.linalg.matrix_rank(w)<w.shape[1]:raise ValueError('Rank deficient')
    weights=w@np.linalg.solve(w.T@w,np.eye(w.shape[1])[0]); fixed=weights[seen]@y[seen]; missing=weights[~seen]*upper[~seen]
    return float(fixed+np.minimum(missing,0).sum()),float(fixed+np.maximum(missing,0).sum())


def scenario(task):
    i,(n,prev,effects,mechanism),reps,seed=task;rng=np.random.default_rng(np.random.SeedSequence([seed,i]));keys=('H2','H3');targets=dict(zip(keys,effects));rows={k:[] for k in keys};bounds={k:[] for k in keys};joint=false=0
    for _ in range(reps):
        g,known,models=generate(n,prev,effects,mechanism,rng); fits={}
        for k,(x,y,seen,upper) in models.items():
            keep=known&seen
            try:fits[k]=fit_arrays(g[keep],x[keep],y[keep])
            except (ValueError,np.linalg.LinAlgError):fits[k]=None
            try:
                lo,hi=outcome_bounds(g[known],x[known],y[known],seen[known],upper[known]);bounds[k].append((hi-lo,lo>0,hi<0,lo<=0<=hi))
            except (ValueError,np.linalg.LinAlgError):pass
        adjusted=holm({k:None if fits[k] is None else fits[k]['p'] for k in keys});rej={k:adjusted[k] is not None and adjusted[k]<=.05 for k in keys};joint+=int(all(rej.values()));false+=int(any(rej[k] and targets[k]==0 for k in keys))
        for k,f in fits.items():
            if f is not None:rows[k].append((f['beta']-targets[k],f['ci'][0]<=targets[k]<=f['ci'][1],rej[k],f['switchers']))
    out={}
    for k in keys:
        a=np.array(rows[k]); b=np.array(bounds[k]);v=len(a);q=len(b)
        out[k]={'valid':v,'failed':reps-v,'bias':float(a[:,0].mean()) if v else None,'coverage':float(a[:,1].sum()/reps) if v else 0.,'rejection':float(a[:,2].sum()/reps) if v else 0.,'mean_switchers':float(a[:,3].mean()) if v else None,'bounds_valid':q,'mean_bound_width':float(b[:,0].mean()) if q else None,'bound_positive':float(b[:,1].sum()/reps) if q else 0.,'bound_negative':float(b[:,2].sum()/reps) if q else 0.,'bound_contains_zero':float(b[:,3].sum()/reps) if q else 0.}
    return {'n':n,'prevalence':prev,'targets':targets,'mechanism':mechanism,'models':out,'joint_rejection':joint/reps,'false_family':false/reps if 0 in effects else None}


def run(reps=200,seed=20261206,workers=1,smoke=False,output=None):
    if reps<1 or workers<1 or seed<0:raise ValueError('Invalid run parameters')
    grid=list(itertools.product((480,640,1000),(.05,.10),((0.,0.),(.4,0.),(0.,-.2),(.4,-.2)),('mcar','mar','joint_mnar')))
    if smoke:grid=[grid[0],grid[-1]]
    report={'status':'SYNTHETIC_DEVELOPMENT','seed':seed,'reps':reps,'planned_cells':len(grid),'complete':False,'screening_only':smoke or reps<1000,'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},'cells':[]}
    path=Path(output) if output else None
    if path:
        if path.exists():raise FileExistsError(path)
        path.parent.mkdir(parents=True,exist_ok=True)
    def save():
        if path:
            tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');tmp.replace(path)
    tasks=[(i,s,reps,seed) for i,s in enumerate(grid)]
    def collect(results):
        for row in results:report['cells'].append(row);save()
    if workers==1:collect(map(scenario,tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:collect(pool.map(scenario,tasks,chunksize=1))
    report['complete']=True;save();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reps',type=int,default=200);p.add_argument('--seed',type=int,default=20261206);p.add_argument('--workers',type=int,default=1);p.add_argument('--smoke',action='store_true');p.add_argument('--output');a=p.parse_args();d=run(a.reps,a.seed,a.workers,a.smoke,a.output)
    if not a.output:print(json.dumps(d,indent=2,allow_nan=False))
