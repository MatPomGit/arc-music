"""Development-only ordinal EFA. Complete cases; explicit sparse-data failures."""
from dataclasses import dataclass
import numpy as np
from scipy.special import ndtr, ndtri, roots_legendre
from scipy.optimize import minimize_scalar, minimize
from scipy.linalg import eigh

_NODES, _WEIGHTS = roots_legendre(32)

def _ordinal(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[0] < 30 or x.shape[1] < 2:
        raise ValueError("need at least 30 rows and two items")
    if not np.all(np.isfinite(x)) or not np.all(np.isin(x, np.arange(5))):
        raise ValueError("complete integer responses 0..4 required")
    x = x.astype(int)
    if any(np.min(np.bincount(col, minlength=5)) < 5 for col in x.T):
        raise ValueError("each category must have at least five observations")
    return x

def thresholds(col):
    counts = np.bincount(col, minlength=5)
    if np.min(counts) < 5:
        raise ValueError("sparse category")
    return ndtri(np.cumsum(counts)[:-1] / len(col))

def rectangle_prob(a, b, rho):
    """Bivariate normal rectangles via deterministic Plackett quadrature."""
    if abs(rho) >= 1:
        raise ValueError("correlation must be interior")
    a, b = np.asarray(a), np.asarray(b)
    t = rho * (_NODES + 1) / 2
    aa, bb = a[:, None, None], b[None, :, None]
    integrand = np.exp(-(aa**2 - 2*t*aa*bb + bb**2)/(2*(1-t*t))) / (2*np.pi*np.sqrt(1-t*t))
    interior = ndtr(a)[:, None]*ndtr(b)[None, :] + rho/2 * (integrand @ _WEIGHTS)
    cdf = np.zeros((len(a)+2, len(b)+2))
    cdf[1:-1, 1:-1] = interior
    cdf[-1, 1:-1] = ndtr(b)
    cdf[1:-1, -1] = ndtr(a)
    cdf[-1, -1] = 1.
    probs = np.diff(np.diff(cdf, axis=0), axis=1)
    if np.min(probs) < -1e-8:
        raise ArithmeticError("invalid bivariate probabilities")
    return np.maximum(probs, 1e-15)

def polychoric_pair(a, b):
    """Two-step maximum likelihood with fixed empirical marginal thresholds."""
    ta, tb = thresholds(a), thresholds(b)
    counts = np.bincount(a*5+b, minlength=25).reshape(5,5)
    def loss(rho):
        return -float(np.sum(counts * np.log(rectangle_prob(ta,tb,rho))))
    fit = minimize_scalar(loss, bounds=(-.98,.98), method="bounded",
                          options={"xatol":1e-6})
    if not fit.success or abs(fit.x) >= .979:
        raise ArithmeticError("polychoric optimisation failed or boundary estimate")
    return float(fit.x)

def polychoric_matrix(x):
    x = _ordinal(x)
    r = np.eye(x.shape[1])
    for i in range(x.shape[1]):
        for j in range(i):
            r[i,j] = r[j,i] = polychoric_pair(x[:,i],x[:,j])
    return r

@dataclass
class ParallelResult:
    observed: np.ndarray
    reference: np.ndarray
    retained: int
    replicates: int

def parallel_analysis(x, replicates=500, seed=20261126):
    """Independent column permutations preserve ordinal marginals.
    Retain consecutive observed eigenvalues exceeding 95th null percentiles.
    No silent exclusion of failed replications.
    """
    x = _ordinal(x)
    if replicates < 10:
        raise ValueError("need at least ten replicates (500 for protocol)")
    rng = np.random.default_rng(seed)
    obs = np.linalg.eigvalsh(polychoric_matrix(x))[::-1]
    null = np.empty((replicates,x.shape[1]))
    for i in range(replicates):
        xp = np.column_stack([rng.permutation(col) for col in x.T])
        null[i] = np.linalg.eigvalsh(polychoric_matrix(xp))[::-1]
    ref = np.quantile(null,.95,axis=0)
    k = 0
    for yes in obs > ref:
        if not yes:
            break
        k += 1
    return ParallelResult(obs,ref,k,replicates)

@dataclass
class EFAResult:
    pattern: np.ndarray
    structure: np.ndarray
    factor_correlation: np.ndarray
    uniqueness: np.ndarray
    rms_residual: float
    min_eigenvalue: float
    near_heywood: bool

def _varimax(a, maxiter=500):
    p,k = a.shape
    rot = np.eye(k)
    old = 0.
    for _ in range(maxiter):
        z = a @ rot
        u,s,v = np.linalg.svd(a.T @ (z**3 - z @ np.diag(np.sum(z*z,axis=0))/p))
        rot = u @ v
        objective = s.sum()
        if abs(objective-old) <= 1e-8*max(1.,objective):
            return a @ rot
        old = objective
    raise ArithmeticError("varimax did not converge")

def minres_promax(r, k):
    """MINRES extraction (off-diagonal residuals) and oblique promax rotation.
    Reject non-positive-definite input rather than silently smoothing it.
    """
    r = np.asarray(r,dtype=float)
    if (r.ndim != 2 or r.shape[0] != r.shape[1] or
            not np.all(np.isfinite(r)) or not np.allclose(r,r.T) or
            not np.allclose(np.diag(r),1)):
        raise ValueError("correlation matrix required")
    p = len(r)
    if not 1 <= k < p or ((p-k)**2-p-k) < 0:
        raise ValueError("invalid or underidentified factor count")
    mineig = float(np.linalg.eigvalsh(r)[0])
    if mineig <= 1e-8:
        raise ArithmeticError("non-positive-definite polychoric matrix")
    off = np.tril_indices(p,-1)
    def load(u):
        vals,vecs = eigh(r-np.diag(u),subset_by_index=[p-k,p-1])
        return vecs[:,::-1]*np.sqrt(np.maximum(vals[::-1],0))
    def loss(u):
        a = load(u)
        return float(np.sum((r-a@a.T)[off]**2))
    initial = np.clip(1/np.diag(np.linalg.inv(r)),.01,.99)
    fit = minimize(loss,initial,method="L-BFGS-B",bounds=[(.005,.999)]*p,
                   options={"maxiter":1000,"ftol":1e-12})
    if not fit.success:
        raise ArithmeticError("MINRES optimisation failed: "+str(fit.message))
    a = load(fit.x)
    if np.linalg.matrix_rank(a) < k:
        raise ArithmeticError("rank-deficient loadings")
    if k == 1:
        pattern, phi = a, np.eye(1)
    else:
        z = _varimax(a)
        target = z * np.abs(z)**3
        transform = np.linalg.lstsq(z,target,rcond=None)[0]
        if np.linalg.cond(transform) > 1e6:
            raise ArithmeticError("ill-conditioned promax transformation")
        inv = np.linalg.inv(transform)
        rawphi = inv @ inv.T
        sd = np.sqrt(np.diag(rawphi))
        phi = rawphi / sd[:,None] / sd[None,:]
        pattern = (z @ transform)*sd
    reproduced = pattern@phi@pattern.T
    unique = 1-np.diag(reproduced)
    near_heywood = bool(np.any(unique <= .01))
    if np.any(unique <= 0):
        raise ArithmeticError("improper uniqueness")
    return EFAResult(pattern,pattern@phi,phi,unique,
                     float(np.sqrt(np.mean((r-reproduced)[off]**2))),
                     mineig,near_heywood)
