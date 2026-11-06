import numpy as np, datetime, json, os
import xarray as xr
Z=np.load('/tmp/sst_region.npz')
S=Z['sst'].astype(np.float64); dates=[datetime.date.fromisoformat(x) for x in Z['dates']]; lat=Z['lat']; lon=Z['lon']
idx={d:i for i,d in enumerate(dates)}
def doy(d):
    return (datetime.date(2000,d.month,d.day)-datetime.date(2000,1,1)).days+1
assert doy(datetime.date(2007,12,31))==366 and doy(datetime.date(2008,12,31))==366 and doy(datetime.date(2008,3,1))==61 and doy(datetime.date(2008,2,28))==59 and doy(datetime.date(2008,2,29))==60 and doy(datetime.date(2007,3,1))==61
bstart=datetime.date(1992,1,1); bend=datetime.date(2002,12,31)
bdates=[bstart+datetime.timedelta(i) for i in range((bend-bstart).days+1)]
pool_dates={k:set() for k in range(1,367)}
for b in bdates:
    k=doy(b)
    if k==60: continue
    for off in range(-5,6):
        pool_dates[k].add(b+datetime.timedelta(off))
thr=np.full((367,)+S.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
for k in range(1,367):
    if k==60: continue
    ds_=sorted(pool_dates[k])
    ii=[idx[x] for x in ds_]
    P=S[ii]
    thr[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(P,axis=0)
    if k in (1,366,59,61): print(k,len(ds_))
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    x=a[1:367]; out=np.empty_like(x)
    for d in range(366):
        ii=[(d+o)%366 for o in range(-15,16)]
        out[d]=np.mean(x[ii],axis=0)
    r=np.full_like(a,np.nan); r[1:367]=out; return r
thrS=smooth(thr); climS=smooth(clim)
tgt_dates=[datetime.date(2007,6,1)+datetime.timedelta(i) for i in range(92)]
sea=np.all(np.isfinite(S[[idx[d] for d in tgt_dates]]),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
print('NaN thr for sea cells:', np.isnan(thrS[1:367][:,sea]).sum(), 'NaN pool in sea:', np.isnan(thr[1:367][:,sea]).sum())
T=len(tgt_dates)
hot=np.zeros((T,)+S.shape[1:],bool)
for j,d in enumerate(tgt_dates):
    hot[j]=(S[idx[d]]>=thrS[doy(d)])&sea
mhw=np.zeros_like(hot)
def runs(x):
    r=[];s=None
    for i,v in enumerate(list(x)+[False]):
        if v and s is None: s=i
        if not v and s is not None: r.append((s,i-1)); s=None
    return r
for i in range(sea.shape[0]):
    for j in range(sea.shape[1]):
        if not sea[i,j]: continue
        rr=[r for r in runs(hot[:,i,j]) if r[1]-r[0]+1>=5]
        merged=[]
        for r in rr:
            if merged and r[0]-merged[-1][1]-1<=2: merged[-1]=(merged[-1][0],r[1])
            else: merged.append(r)
        for a,b in merged: mhw[a:b+1,i,j]=True
active=mhw.any(axis=(1,2))
ev=[]; s=None
for j,v in enumerate(list(active)+[False]):
    if v and s is None: s=j
    if not v and s is not None: ev.append((tgt_dates[s],tgt_dates[j-1])); s=None
print('events',[(a.isoformat(),b.isoformat()) for a,b in ev])
print('active days',active.sum(),'mhw cell-days',mhw.sum(),'hot cell-days',hot.sum())