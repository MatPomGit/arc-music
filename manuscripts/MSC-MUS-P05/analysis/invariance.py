"""Development two-group ordinal invariance diagnostics.

Group-specific standardized probit CFA. Tests restrictions implied by
common thresholds, loadings and intercepts under positive item response
scales and freely varying group factor means/variances. Not a nested
multi-group WLSMV fit; no latent mean estimates are issued.
"""
from dataclasses import dataclass
import numpy as np
from scipy.special import ndtr
from scipy.stats import norm, chi2
from robust_cfa import robust_fit
from ordinal_efa import _ordinal

def contrasts(a,b,domains):
    """Affine-link restrictions using the outer thresholds as anchors.

    Each group has zero item-response mean and unit variance internally.
    With common thresholds, scale = range(t_ref)/range(t_other);
    shift = t_ref[0] - scale*t_other[0].
    The two internal normalized threshold locations must agree.
    With equal unstandardized loadings, scale*l_other/l_ref is constant
    within each domain (group factor SD).
    With equal intercepts, shift/l_ref is constant within each domain
    (group factor mean). These restrictions are scale-aware, unlike
    directly testing equality of standardized loadings or raw thresholds.
    """
    d=np.asarray(domains); p=len(d)
    a=np.asarray(a,float); b=np.asarray(b,float)
    if a.shape!=(5*p,) or b.shape!=(5*p,) or not np.isfinite(np.r_[a,b]).all():
        raise ValueError("loadings and four thresholds per item required")
    l1,l2=a[:p],b[:p]
    if np.any(l1<=.15) or np.any(l2<=.15):
        raise ValueError("weak/nonpositive loadings; anchor link unsupported")
    t1=a[p:].reshape(p,4); t2=b[p:].reshape(p,4)
    if np.any(np.diff(t1,axis=1)<=0) or np.any(np.diff(t2,axis=1)<=0):
        raise ValueError("unordered thresholds")
    width1=t1[:,-1]-t1[:,0]; width2=t2[:,-1]-t2[:,0]
    scale=width1/width2
    shift=t1[:,0]-scale*t2[:,0]
    shape=(t1[:,1:3]-t1[:,[0]])/width1[:,None]-(t2[:,1:3]-t2[:,[0]])/width2[:,None]
    metric=np.log(scale*l2/l1)
    location=shift/l1
    m=[]; s=[]
    for group in np.unique(d):
        idx=np.flatnonzero(d==group)
        if len(idx)<3:
            raise ValueError("at least three items per domain")
        m.extend(metric[idx[1:]]-metric[idx[0]])
        s.extend(location[idx[1:]]-location[idx[0]])
    return np.r_[shape.ravel(),m,s]

def _moments(x,d):
    x=_ordinal(x)
    f=robust_fit(x,d)
    p=len(d); t=f.fit.thresholds
    threshold_if=((x[:,:,None]<=np.arange(4))-ndtr(t)[None,:,:])/norm.pdf(t)[None,:,:]
    joint=np.column_stack([f.parameter_influence[:,:p],threshold_if.reshape(len(x),4*p)])
    joint-=joint.mean(axis=0)
    return np.r_[f.fit.loadings,t.ravel()],joint.T@joint/(len(x)*(len(x)-1)),f

def _jacobian(a,b,d,h=1e-5):
    q=np.r_[a,b]; n=len(a)
    out=np.empty((len(contrasts(a,b,d)),len(q)))
    for j in range(len(q)):
        v=q.copy(); w=q.copy()
        v[j]+=h; w[j]-=h
        out[:,j]=(contrasts(v[:n],v[n:],d)-contrasts(w[:n],w[n:],d))/(2*h)
    return out

def wald(value,cov):
    value=np.asarray(value,float); cov=np.asarray(cov,float)
    if cov.shape!=(len(value),len(value)) or np.linalg.eigvalsh(cov)[0]<=0 or np.linalg.cond(cov)>1e10:
        raise ArithmeticError("singular or ill-conditioned contrast covariance")
    stat=float(value@np.linalg.solve(cov,value))
    return {"statistic":stat,"df":len(value),"p_value":float(chi2.sf(stat,len(value)))}

def compare_groups(x1,x2,domains,min_group=150):
    """Independent groups, fixed item order/assignment; complete records only.

    The cumulative Wald tests form an ordered diagnostic sequence. Failed
    earlier gates prevent escalation; non-rejection is not proof of invariance.
    No data-driven anchor deletion, no group mean estimates.
    """
    d=np.asarray(domains); p=len(d)
    if min_group<30 or min(len(x1),len(x2))<min_group:
        raise ValueError("insufficient group size")
    if np.asarray(x1).shape[1]!=p or np.asarray(x2).shape[1]!=p:
        raise ValueError("item mismatch")
    a,va,f1=_moments(x1,d); b,vb,f2=_moments(x2,d)
    value=contrasts(a,b,d); J=_jacobian(a,b,d); q=len(a)
    cov=J[:,:q]@va@J[:,:q].T+J[:,q:]@vb@J[:,q:].T
    m=p-len(np.unique(d))
    tests={}
    for name,end in [("threshold_shape",2*p),("threshold_loading",2*p+m),
                     ("threshold_loading_intercept",2*p+2*m)]:
        tests[name]=wald(value[:end],cov[:end,:end])
    configural=[f1.p_value,f2.p_value]
    # Two group model-fit tests; Bonferroni .025 each.
    gate="configural_not_rejected" if min(configural)>=.025 else "configural_rejected"
    if gate=="configural_not_rejected":
        for name,test in tests.items():
            if test["p_value"]<.05:
                gate=name+"_rejected"; break
        else:
            gate="all_restrictions_not_rejected"
    from invariance_family import global_decision
    return {"global_family_candidate":global_decision(configural,tests),
            "group_sizes":[len(x1),len(x2)],"configural_p_values":configural,
            "tests":tests,"ordered_gate":gate,"latent_mean_comparison_authorized":False,
            "label":"development ordinal invariance diagnostics; not nested WLSMV"}
