import numpy as np, datetime as dt, json, os, xarray as xr, warnings
warnings.filterwarnings('ignore')
z=np.load('/tmp/sub.npz'); A=z['A']; dates=[dt.date.fromisoformat(s) for s in z['dates']]; latv=z['lat']; lonv=z['lon']
def doy(x):
    leap=(x.year%4==0 and x.year%100!=0) or x.year%400==0
    t=x.timetuple().tm_yday
    if leap: return t
    return t+1 if x.month>=3 else t
idx={x:i for i,x in enumerate(dates)}
ny,nx=A.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
base=[x for x in dates if dt.date(1992,1,1)<=x<=dt.date(2002,12,31)]
bydoy={}
for b in base: bydoy.setdefault(doy(b),[]).append(b)
for dd in range(1,367):
    if dd==60: continue
    ids=set()
    for b in bydoy.get(dd,[]):
        for k in range(-5,6):
            x=b+dt.timedelta(k)
            if x in idx: ids.add(idx[x])
    ids=sorted(ids)
    P=A[ids]
    thr[dd]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.empty_like(a)
    v=a[1:367]  # days 1..366 -> index 0..365
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i+1]=v[ii].mean(axis=0)
    return out
# proper smoothing on 366-element array
T=thr[1:367]; C=clim[1:367]
def sm(a):
    return np.array([a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0) for i in range(366)])
Ts=sm(T); Cs=sm(C)
print(np.isnan(Ts[:,0,0]).sum(), np.isnan(Ts).any(axis=0).sum(), np.isnan(Ts[0]).sum())
# target
tgt=[x for x in dates if dt.date(2016,6,1)<=x<=dt.date(2016,8,31)]
ti=[idx[x] for x in tgt]
S=A[ti]
sea=np.all(np.isfinite(S),axis=0)
print('sea cells', sea.sum(), 'target days', len(tgt))
print('sea cells with any NaN in full baseline?', np.isfinite(Ts).all(axis=0).sum())