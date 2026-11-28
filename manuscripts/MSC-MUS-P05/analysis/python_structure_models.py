"""Python ordinal moment-model development; NOT WLSMV or an independent benchmark.

Fit one factor, seven correlated factors and one higher-order factor to the
same ordinal moments. The residual test is a moment-matched approximation.
The historical external reference gate remains blocked.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import chi2

from ordinal_cfa import fit_moments
from robust_cfa import _model_jacobian


METHOD = "ordinal_dwls_moment_matched_development_v1"
MODELS = ("one_factor", "correlated_seven", "higher_order")


def higher_moments(corr, weights, domains):
    """Second-order covariance restriction phi_ab = g_a*g_b for a != b."""
    d = np.asarray(domains)
    p = len(d)
    k = len(np.unique(d))
    if k < 3 or not np.array_equal(np.unique(d), np.arange(k)):
        raise ValueError("Higher-order model requires contiguous domains, k >= 3")
    if min(np.bincount(d)) < 3:
        raise ValueError("At least three indicators per domain")
    i, j = np.tril_indices(p, -1)
    di, dj = d[i], d[j]
    cross = di != dj
    rows = np.arange(len(i))
    corr, weights = np.asarray(corr, float), np.asarray(weights, float)
    if corr.shape != i.shape or weights.shape != i.shape or not np.isfinite(corr).all() or not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("Invalid ordinal moments")
    anchors = [np.flatnonzero(d == a)[0] for a in range(k)]
    lower = np.full(p+k, -.995)
    upper = np.full(p+k, .995)
    lower[anchors] = .005
    lower[p] = .005
    scale = np.sqrt(weights)

    def prediction(theta):
        l, g = theta[:p], theta[p:]
        phi = np.outer(g, g) + np.diag(1-g*g)
        return l[i]*l[j]*phi[di, dj], phi

    def jacobian(theta):
        l, g = theta[:p], theta[p:]
        phi = np.outer(g, g) + np.diag(1-g*g)
        J = np.zeros((len(i), p+k))
        J[rows, i] = l[j]*phi[di, dj]
        J[rows, j] = l[i]*phi[di, dj]
        for a in range(k):
            m = cross & (di == a)
            J[m, p+a] = l[i[m]]*l[j[m]]*g[dj[m]]
            m = cross & (dj == a)
            J[m, p+a] = l[i[m]]*l[j[m]]*g[di[m]]
        return J

    fits = []
    for l, g in ((.45, .35), (.65, .60), (.75, .80)):
        f = least_squares(lambda t: scale*(corr-prediction(t)[0]),
                          np.r_[np.full(p, l), np.full(k, g)],
                          jac=lambda t: -scale[:, None]*jacobian(t),
                          bounds=(lower, upper), max_nfev=1000,
                          ftol=1e-9, xtol=1e-9, gtol=1e-9)
        if f.success and np.isfinite(f.cost):
            fits.append(f)
    if not fits:
        raise ArithmeticError("Higher-order fit did not converge")
    f = min(fits, key=lambda a: a.cost)
    expected, phi = prediction(f.x)
    minimum_uniqueness = float(np.min(1-f.x[:p]**2))
    minimum_factor_eigenvalue = float(np.min(np.linalg.eigvalsh(phi)))
    J = jacobian(f.x)
    proper = (np.linalg.matrix_rank(J) == p+k
              and minimum_uniqueness > .01 and minimum_factor_eigenvalue > .01
              and np.min(1-f.x[p:]**2) > .01 and not np.any(f.active_mask))
    return expected, J, minimum_uniqueness, minimum_factor_eigenvalue, proper


def development_test(corr, expected, J, influence):
    n = len(influence)
    w = 1/(np.sum(influence*influence, axis=0)/(n-1))
    Jw = J*np.sqrt(w)[:, None]
    bread = Jw.T@Jw
    if np.linalg.matrix_rank(Jw) != Jw.shape[1] or np.linalg.cond(bread) > 1e10:
        raise ArithmeticError("Ill-conditioned moment model")
    weighted_if = influence*np.sqrt(w)
    residual_if = weighted_if-(Jw@np.linalg.solve(bread, Jw.T@weighted_if.T)).T
    A = residual_if.T@residual_if/(n-1)
    tr, tr2 = np.trace(A), np.sum(A*A)
    if min(tr, tr2) <= 1e-10:
        raise ArithmeticError("Degenerate residual test")
    statistic = n*np.sum(w*(corr-expected)**2)
    scale, df = tr2/tr, tr*tr/tr2
    return {"p_development": float(chi2.sf(statistic/scale, df)),
            "nominal_df": len(corr)-J.shape[1],
            "effective_df": float(df), "statistic": float(statistic),
            "srmr": float(np.sqrt(np.mean((corr-expected)**2)))}


def fit_development_model(moments, model):
    if model not in MODELS:
        raise ValueError("Unknown model")
    p = len(moments.cuts)
    if p != 35 or len(moments.influence) <= p:
        raise ValueError("35 items and more than 35 complete records required")
    influence = moments.influence
    var = np.sum(influence*influence, axis=0)/(len(influence)-1)
    if not np.isfinite(var).all() or np.any(var <= 1e-10):
        raise ArithmeticError("Degenerate moment variance")
    w = 1/var
    d = np.zeros(p, int) if model == "one_factor" else np.repeat(np.arange(7), 5)
    if model == "higher_order":
        expected, J, u, e, proper = higher_moments(moments.correlations, w, d)
    else:
        f = fit_moments(moments.correlations, w, moments.cuts, d)
        expected, J = _model_jacobian(f.loadings, f.phi, d)
        u, e = float(np.min(f.uniqueness)), float(np.min(np.linalg.eigvalsh(f.phi)))
        proper = f.proper
    result = {"method": METHOD, "model": model,
              "status": "PROPER" if proper else "IMPROPER",
              "minimum_uniqueness": u, "minimum_factor_eigenvalue": e,
              "independent_reference_verified": False}
    if proper:
        result.update(development_test(moments.correlations, expected, J, influence))
    return result
