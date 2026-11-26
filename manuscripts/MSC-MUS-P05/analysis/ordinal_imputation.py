"""Development Bayesian ordinal-probit chained imputation and Rubin pooling.

Conditional models use observed outcomes, current other-item values and
fully observed auxiliaries. FCS compatibility and inferential calibration
are not assumed. Delta sensitivity applies only to missing outcomes.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import cho_factor,cho_solve,solve_triangular
from scipy.stats import truncnorm,t,norm
from robust_cfa import robust_fit
from chain_diagnostics import summarize

def _validate(x,z):
    x=np.asarray(x,float); z=np.asarray(z,float)
    if x.ndim!=2 or len(x)<30 or x.shape[1]<2 or z.ndim!=2 or len(z)!=len(x):
        raise ValueError("invalid input dimensions")
    if np.isinf(x).any() or not np.isfinite(z).all() or not np.isin(x[np.isfinite(x)],np.arange(5)).all():
        raise ValueError("ordinal 0..4 and finite auxiliaries required")
    for col in x.T:
        count=np.bincount(col[np.isfinite(col)].astype(int),minlength=5)
        if count.min()<5:
            raise ValueError("each observed category requires five responses")
    if z.shape[1]:
        sd=z.std(axis=0)
        if np.any(sd<=0):
            raise ValueError("constant auxiliary")
        z=(z-z.mean(axis=0))/sd
    return x,z

@dataclass
class State:
    beta: np.ndarray
    cuts: np.ndarray

def _step(state,design,y,rng,steps=5):
    """Gibbs transitions for ordinal probit, first threshold fixed at zero.

    beta ~ N(0,4I); remaining ordered positive thresholds have independent
    normal priors (conditional on order), means .6,1.2,1.8 and SD 2.
    Residual variance fixed at one. Draws use observed target outcomes only.
    """
    precision=design.T@design+np.eye(design.shape[1])/4
    chol=np.linalg.cholesky(precision)
    factor=cho_factor(precision,lower=True)
    for _ in range(steps):
        bounds=np.r_[-np.inf,state.cuts,np.inf]
        mu=design@state.beta
        latent=truncnorm.rvs(bounds[y]-mu,bounds[y+1]-mu,loc=mu,
                            random_state=rng)
        mean=cho_solve(factor,design.T@latent)
        state.beta=mean+solve_triangular(chol.T,rng.normal(size=len(mean)),lower=False)
        for k in range(1,4):
            lo=max(state.cuts[k-1],float(latent[y==k].max()))
            hi=min(state.cuts[k+1] if k<3 else np.inf,float(latent[y==k+1].min()))
            if not lo<hi:
                raise ArithmeticError("invalid latent threshold interval")
            prior_mean=.6*k
            state.cuts[k]=truncnorm.rvs((lo-prior_mean)/2,(hi-prior_mean)/2,
                                       loc=prior_mean,scale=2,random_state=rng)
    return state

def impute(x,z,m=50,sweeps=100,gibbs_steps=5,delta=0.,seed=20261126):
    """Independent seeded chains, one retained completed data set each.

    Predictor encoding: centered numeric ordinal items and standardized
    auxiliaries. The working MAR assumption is conditional on these inputs.
    Delta shifts the latent probit mean for missing entries (in residual SD).
    Observed entries are never overwritten.
    """
    x,z=_validate(x,z)
    if m<2 or sweeps<1 or gibbs_steps<1:
        raise ValueError("insufficient chains or transitions")
    n,p=x.shape
    delta=np.broadcast_to(np.asarray(delta,float),(p,))
    if not np.isfinite(delta).all() or np.max(abs(delta))>3:
        raise ValueError("delta outside prespecified range [-3,3]")
    missing=np.isnan(x)
    children=np.random.SeedSequence(seed).spawn(m)
    result=[]; diagnostics=[]
    for child in children:
        rng=np.random.default_rng(child); y=x.copy(); states={}
        for j in np.flatnonzero(missing.any(axis=0)):
            obs=~missing[:,j]
            y[~obs,j]=rng.choice(y[obs,j],size=(~obs).sum())
            states[j]=State(np.zeros(p+z.shape[1]),np.array([0.,.6,1.2,1.8]))
        trace=[]; item_traces={str(j):[] for j in states}
        for sweep in range(sweeps):
            for j in rng.permutation(list(states)):
                obs=~missing[:,j]
                design=np.column_stack([np.ones(n),(np.delete(y,j,axis=1)-2)/2,z])
                state=_step(states[j],design[obs],x[obs,j].astype(int),rng,gibbs_steps)
                latent=design[~obs]@state.beta+rng.normal(size=(~obs).sum())+delta[j]
                y[~obs,j]=np.digitize(latent,state.cuts)
            if sweep>=sweeps//2:
                trace.append(float(y[missing].mean()) if missing.any() else None)
                for j in states:
                    item_traces[str(j)].append(float(y[missing[:,j],j].mean()))
        if not np.array_equal(y[~missing],x[~missing]) or not np.isin(y,np.arange(5)).all():
            raise ArithmeticError("imputation violated observed/category constraints")
        result.append(y.astype(int))
        diagnostics.append({"missing_mean_trace":trace,"item_mean_traces":item_traces,
                            "final_missing_means":[float(y[missing[:,j],j].mean())
                            if missing[:,j].any() else None for j in range(p)]})
    return result,diagnostics

def rubin_pool(estimates,covariances):
    """Multivariate Rubin covariance; scalar Rubin t intervals.

    Large complete-data df approximation, not Barnard-Rubin adjustment.
    Pool parameters only; fit-test statistics are not Rubin-pooled.
    """
    q=np.asarray(estimates,float); u=np.asarray(covariances,float)
    if q.ndim!=2 or len(q)<2 or u.shape!=(len(q),q.shape[1],q.shape[1]) or not np.isfinite(q).all() or not np.isfinite(u).all():
        raise ValueError("valid estimates and covariances required")
    if not np.allclose(u,u.transpose(0,2,1)) or any(np.linalg.eigvalsh(a)[0]<-1e-10 for a in u):
        raise ValueError("invalid within-imputation covariance")
    m=len(q); mean=q.mean(axis=0); within=u.mean(axis=0)
    centered=q-mean; between=centered.T@centered/(m-1)
    total=within+(1+1/m)*between
    variance=np.diag(total)
    if np.any(variance<=0):
        raise ArithmeticError("nonpositive pooled variance")
    fraction=(1+1/m)*np.diag(between)/variance
    df=np.full(len(mean),np.inf)
    positive=fraction>1e-12
    df[positive]=(m-1)/fraction[positive]**2
    critical=t.ppf(.975,df)
    intervals=np.column_stack([mean-critical*np.sqrt(variance),mean+critical*np.sqrt(variance)])
    return {"estimates":mean,"within":within,"between":between,"covariance":total,
            "intervals":intervals,"df":df,"missing_information_component":fraction}

def fit_multiple(x,z,domains,**kwargs):
    completed,diagnostics=impute(x,z,**kwargs)
    fits=[]; failures={}
    for y in completed:
        try:
            fits.append(robust_fit(y,domains))
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
            key=str(exc); failures[key]=failures.get(key,0)+1
    # Strict gate: excluding failed draws can bias pooling.
    pooled=rubin_pool([f.parameters for f in fits],[f.covariance for f in fits]) if not failures else None
    return {"requested":len(completed),"proper":len(fits),"failures":failures,
            "pooled":pooled,"diagnostics":diagnostics,"chain_screen":summarize(diagnostics)}
