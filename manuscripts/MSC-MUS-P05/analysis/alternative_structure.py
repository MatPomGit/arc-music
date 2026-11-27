"""Alternative ordinal generating structures for P05; historical DGP unchanged."""
import numpy as np

STRUCTURES=("one_factor","higher_order","correlated_seven")
HIGHER_LOADINGS=np.array([.45,.50,.55,.60,.65,.70,.75])

def factor_covariance(structure):
    if structure=="one_factor":
        return np.ones((1,1))
    if structure=="higher_order":
        return np.outer(HIGHER_LOADINGS,HIGHER_LOADINGS)+np.diag(1-HIGHER_LOADINGS**2)
    if structure=="correlated_seven":
        # Two distinct correlated blocks; not representable by one general
        # factor with independent first-order residuals (tetrad violation).
        block=np.array([0,0,0,1,1,1,1])
        return np.where(block[:,None]==block[None,:],.55,.15)+np.eye(7)*.45
    raise ValueError("Unknown generating structure")

def generate(n,structure,rng,loading=.65,skew=False,missing=0.):
    if n<30 or not 0<loading<1 or not 0<=missing<1:
        raise ValueError("Invalid generating parameters")
    phi=factor_covariance(structure)
    if structure=="one_factor":
        latent=rng.normal(size=(n,1))
        domain=np.repeat(latent,35,axis=1)
    elif structure=="higher_order":
        general=rng.normal(size=(n,1))
        latent=general*HIGHER_LOADINGS+rng.normal(size=(n,7))*np.sqrt(1-HIGHER_LOADINGS**2)
        domain=np.repeat(latent,5,axis=1)
    else:
        # Construct covariance by independent common, block and unique factors.
        global_factor=rng.normal(size=(n,1))
        block=rng.normal(size=(n,2))[:,[0,0,0,1,1,1,1]]
        latent=np.sqrt(.15)*global_factor+np.sqrt(.40)*block+np.sqrt(.45)*rng.normal(size=(n,7))
        domain=np.repeat(latent,5,axis=1)
    z=loading*domain+np.sqrt(1-loading**2)*rng.normal(size=(n,35))
    cuts=[-.2,.35,.85,1.35] if skew else [-.85,-.25,.25,.85]
    x=np.digitize(z,cuts).astype(float)
    if missing:x[rng.random(x.shape)<missing]=np.nan
    return x
