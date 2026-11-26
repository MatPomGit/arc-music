"""Exact noncentral-t planning sensitivity, not a final recruitment decision."""
import math,json
from scipy.stats import nct,t
def power(n,d,alpha=.05):
    if n<4 or n%2 or d<=0 or not 0<alpha<1:raise ValueError("Invalid balanced design")
    q=t.ppf(1-alpha/2,n-2);nc=d*math.sqrt(n/4)
    return float(nct.sf(q,n-2,nc)+nct.cdf(-q,n-2,nc))
def plan(d,loss=.2,target=.9):
    if d<=0 or not 0<=loss<1 or not .05<target<1:raise ValueError("Invalid planning inputs")
    n=4
    while power(n,d)<target:n+=2
    return dict(d=d,complete=n,randomised=2*math.ceil(n/(1-loss)/2),power=power(n,d),expected_loss=loss)
if __name__=="__main__":
    print(json.dumps([plan(d) for d in (.2,.25,.3,.35,.4)],indent=2))
