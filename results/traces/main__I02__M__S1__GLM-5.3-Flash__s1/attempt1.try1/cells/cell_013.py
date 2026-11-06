import numpy as np
rng=np.random.default_rng(0)
x=rng.random(137)
P=0.9
n=x.size; h=(n-1)*P+1.0; fl=np.floor(h); lo=int(max(fl-1,0)); hi=int(np.ceil(h)-1); gamma=h-fl
mine=x[lo]+(x[hi]-x[lo])*gamma
mine2=x[hi]-(x[hi]-x[lo])*(1.0-gamma) if gamma>=0.5 else mine
npq=np.quantile(x,P,method='hazen')
print("h:",h,"lo:",lo,"hi:",hi,"gamma:",gamma)
print("mine:",mine,"mine2:",mine2,"numpy:",npq)
# test where gamma<0.5 and lo!=hi
xs=np.arange(10.0)
for P in [0.05,0.1,0.2,0.25,0.3,0.35,0.9,0.95]:
    n=xs.size; h=(n-1)*P+1.0; fl=np.floor(h); lo=int(max(fl-1,0)); hi=int(np.ceil(h)-1); gamma=h-fl
    v=np.quantile(xs,P,method='hazen')
    formula=xs[lo]+(xs[hi]-xs[lo])*gamma
    formula2=xs[hi]-(xs[hi]-xs[lo])*(1.0-gamma) if gamma>=0.5 else formula
    print(P, h, v, formula, formula2, "match:", np.isclose(v,formula2) and np.isclose(v,formula))
