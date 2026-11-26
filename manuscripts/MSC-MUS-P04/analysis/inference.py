"""MSC-MUS-P04 prospective inference; no participant data bundled."""
import numpy as np
from scipy import stats
from scipy.special import expit
from scipy.optimize import minimize

def design(arm, moderator, covariates):
    a = np.asarray(arm, float)
    d = np.asarray(moderator, float)
    c = np.asarray(covariates, float)
    if a.ndim != 1 or d.shape != a.shape or c.ndim != 2 or c.shape[0] != len(a):
        raise ValueError("Incompatible baseline dimensions")
    if set(np.unique(a)) != {0., 1.} or not np.isfinite(d).all() or not np.isfinite(c).all():
        raise ValueError("Both arms and complete finite baseline data required")
    sd = d.std(ddof=1)
    if sd <= 0:
        raise ValueError("Constant moderator")
    d = (d-d.mean())/sd
    a = a-.5
    return np.column_stack((np.ones(len(a)), a, d, a*d, c))

def composite(fit, meaningful):
    """1 = meaningful sketch, 0 = confirmed absent, NaN = unknown."""
    f, m = np.asarray(fit, float), np.asarray(meaningful, float)
    if f.shape != m.shape or f.ndim != 1:
        raise ValueError("Shape mismatch")
    if np.isinf(f).any() or np.isinf(m).any():
        raise ValueError("Infinity invalid")
    if np.any(~np.isin(m[~np.isnan(m)], [0,1])) or np.any((f < 0)|(f > 10)):
        raise ValueError("Invalid status or rating")
    if np.any((m != 1)&np.isfinite(f)):
        raise ValueError("Fit rating requires confirmed meaningful sketch")
    return np.where(m == 0, 0., np.where(m == 1, f, np.nan))

def fit_hc3(x, y):
    x, y = np.asarray(x,float), np.asarray(y,float)
    if x.ndim != 2 or y.shape != (len(x),) or not np.isfinite(x).all():
        raise ValueError("Invalid model data")
    if np.isinf(y).any():
        raise ValueError("Infinite outcome")
    mask = np.isfinite(y)
    x, y = x[mask], y[mask]
    n, p = x.shape
    if n <= p or np.linalg.matrix_rank(x) < p:
        raise ValueError("Insufficient data or rank deficiency")
    inv = np.linalg.inv(x.T@x)
    b = inv@x.T@y
    h = np.einsum("ij,jk,ik->i", x, inv, x)
    if np.any(h >= 1-1e-10):
        raise ValueError("Unit leverage")
    u = (y-x@b)/(1-h)
    v = inv@((x*u[:,None]).T@(x*u[:,None]))@inv
    return b, v, n-p

def contrast(b, v, df, weights):
    w = np.asarray(weights,float)
    est = float(w@b)
    se = float(np.sqrt(max(0.,w@v@w)))
    if se <= 0 or df <= 0:
        raise ValueError("Degenerate contrast")
    q = stats.t.ppf(.975,df)
    return dict(estimate=est,se=se,lower=est-q*se,upper=est+q*se,
                p=float(2*stats.t.sf(abs(est/se),df)),df=float(df))

def target_weights(x, moderator=None):
    w=np.zeros(x.shape[1])
    if moderator is None:
        w[3]=1
    else:
        w[1]=1
        w[3]=moderator
    return w

def availability(x,y):
    obs=np.isfinite(y).astype(float)
    if obs.min()==obs.max():
        prob=np.full(len(y),obs[0])
    else:
        def loss(b):
            z=x@b
            return np.logaddexp(0,z).sum()-obs@z+1e-6*(b@b)
        def grad(b):
            return x.T@(expit(x@b)-obs)+2e-6*b
        opt=minimize(loss,np.zeros(x.shape[1]),jac=grad,method="BFGS")
        if not opt.success and np.max(np.abs(grad(opt.x)))>1e-4:
            raise ValueError("Availability fit failed")
        prob=expit(x@opt.x)
    return {str(int(a+.5)): {"observed_fraction":float(obs[x[:,1]==a].mean()),
             "probability_quantiles":np.quantile(prob[x[:,1]==a],[0,.05,.5,.95,1]).tolist()}
            for a in (-.5,.5)}

def impute_pmm(x,y,m=50,seed=20261126,k=5):
    """Arm-specific posterior linear draws; nearest observed donor, no clipping needed."""
    y=np.asarray(y,float)
    if m<2 or k<1 or np.isinf(y).any() or np.any((y<0)|(y>10)):
        raise ValueError("Invalid imputation inputs")
    rng=np.random.default_rng(seed)
    completed=np.repeat(y[None,:],m,axis=0)
    for arm in (-.5,.5):
        obs=(x[:,1]==arm)&np.isfinite(y)
        mis=(x[:,1]==arm)&np.isnan(y)
        if not mis.any():
            continue
        # Intercept, standardised moderator and baseline covariates.
        z=x[:,[0,2,*range(4,x.shape[1])]]
        zo,zm=z[obs],z[mis]
        yo=y[obs]
        n,p=zo.shape
        if n<=p or n<k or np.linalg.matrix_rank(zo)<p:
            raise ValueError("Insufficient arm-specific donors or rank")
        inv=np.linalg.inv(zo.T@zo)
        b=inv@zo.T@yo
        rss=float(np.sum((yo-zo@b)**2))
        chol=np.linalg.cholesky(inv)
        for j in range(m):
            sigma2=rss/rng.chisquare(n-p)
            draw=b+np.sqrt(sigma2)*(chol@rng.normal(size=p))
            dist=np.abs((zm@draw)[:,None]-(zo@b)[None,:])
            nearest=np.argpartition(dist,k-1,axis=1)[:,:k]
            chosen=nearest[np.arange(len(zm)),rng.integers(k,size=len(zm))]
            completed[j,mis]=yo[chosen]
    if not np.isfinite(completed).all():
        raise ValueError("Incomplete imputation")
    return completed

def pooled_contrast(x, completed, weights):
    fits=[fit_hc3(x,y) for y in completed]
    w=np.asarray(weights)
    q=np.array([w@b for b,v,df in fits])
    u=np.array([w@v@w for b,v,df in fits])
    m=len(q)
    ub=float(u.mean())
    between=float(q.var(ddof=1))
    total=ub+(1+1/m)*between
    if total<=0:
        raise ValueError("Degenerate pooled variance")
    lam=(1+1/m)*between/total
    nu_com=fits[0][2]
    nu_obs=(nu_com+1)/(nu_com+3)*nu_com*(1-lam)
    nu_old=(m-1)/lam**2 if lam>0 else np.inf
    df=1/(1/nu_old+1/nu_obs)
    return contrast(np.array([q.mean()]),np.array([[total]]),df,[1.])

def shift_imputed(x,y,completed,offset0,offset1,slope):
    result=completed.copy()
    missing=np.isnan(y)
    offset=np.where(x[:,1]==.5,offset1,offset0)+slope*x[:,1]*x[:,2]
    result[:,missing]=np.clip(result[:,missing]+offset[missing],0,10)
    return result

def analyze(x,y,m=50,seed=20261126,grid=True):
    w=target_weights(x)
    b,v,df=fit_hc3(x,y)
    completed=impute_pmm(x,y,m,seed)
    pooled=pooled_contrast(x,completed,w)
    result={"complete_outcome":contrast(b,v,df,w),"mar":pooled,
            "availability":availability(x,y),
            "assignment_contrasts":{str(d):pooled_contrast(x,completed,target_weights(x,d))
                                     for d in (-1,0,1)}}
    if grid:
        result["sensitivity"]=[{"offset_control":i,"offset_scaffold":j,"differential_slope":s,
             **pooled_contrast(x,shift_imputed(x,y,completed,i,j,s),w)}
             for i in (-2,0,2) for j in (-2,0,2) for s in (-1,0,1)]
    return result
