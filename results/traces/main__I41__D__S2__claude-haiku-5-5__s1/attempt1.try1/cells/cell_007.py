
import warnings; warnings.filterwarnings('ignore')
import xarray as xr, numpy as np, pandas as pd, json, os
# target subset
tmask=(T>=tgt_start)&(T<=tgt_end)
At=A[tmask]; Tt=T[tmask]
sea=np.all(np.isfinite(At),axis=0)  # (lat,lon)
print('sea cells', sea.sum(), 'of', sea.size, 'target days', len(Tt), Tt[0], Tt[-1])
# check NaN per cell in threshold for sea cells
dt=doy_of(Tt).values if hasattr(doy_of(Tt),'values') else np.array(doy_of(Tt))
thr_t=thr_s[dt-1]  # (ntarget, lat, lon)
print('sea cells with NaN threshold on target days:', np.sum(sea & np.isnan(thr_t).any(axis=0)))
print('target days doy range', dt.min(), dt.max())
hot=(At>=thr_t)  # NaN -> False
hot &= sea[None]
mhw=np.zeros_like(hot)
ntd,nla,nlo=hot.shape
for i in range(nla):
    for j in range(nlo):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        runs=[]; k=0
        while k<ntd:
            if h[k]:
                s=k
                while k<ntd and h[k]: k+=1
                if k-s>=5: runs.append([s,k-1])
            else: k+=1
        # join runs separated by 1-2 non-hot days
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1<=2:
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for s,e in merged: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; k=0
while k<ntd:
    if active[k]:
        s=k
        while k<ntd and active[k]: k+=1
        events.append({"onset":str(Tt[s].date()),"end":str(Tt[k-1].date())})
    else: k+=1
print(events, mhw.sum())
