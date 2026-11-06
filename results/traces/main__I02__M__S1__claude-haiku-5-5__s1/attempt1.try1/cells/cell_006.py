import numpy as np, datetime as dt, json, os
import xarray as xr
z=np.load('/tmp/sub.npz'); A=z['A']; days=[dt.date.fromisoformat(s) for s in z['days']]; LAT=z['lat']; LON=z['lon']
# verify time coordinate matches filename for a few files
for dd in [days[0],days[500],days[-1]]:
    with xr.open_dataset(f"{d}/sst_{dd:%Y%m%d}.nc",engine='h5netcdf') as x: assert str(x.time.values[0])[:10]==dd.isoformat(), (dd,x.time.values)
def doy(t):
    # leap-year-based mapping: Feb29=60; non-leap Mar1=61 handled by month/day
    if t.month==2 and t.day==29: return 60
    base=dt.date(2001,t.month,t.day)  # non-leap year
    n=(base-dt.date(2001,1,1)).days+1
    return n if (t.month,t.day)<(2,29) else n+(1 if (t.month>2 or (t.month==2 and t.day>29)) else 0)*0
# simpler explicit mapping via non-leap for Mar..Dec and direct for Jan-Feb
def doy2(t):
    if t.month==2 and t.day==29: return 60
    n=(dt.date(2001,t.month,t.day)-dt.date(2001,1,1)).days+1
    return n
print(doy2(dt.date(2004,2,28)),doy2(dt.date(2004,3,1)),doy2(dt.date(2004,12,31)),doy2(dt.date(2003,12,31)),doy2(dt.date(2004,6,1)))
# baseline dates
bstart,bend=dt.date(1992,1,1),dt.date(2002,12,31)
baseDates=[]; s=bstart
while s<=bend: baseDates.append(s); s+=dt.timedelta(1)
idx={t:i for i,t in enumerate(days)}
# SST by date for baseline (in loaded array)
ndays=len(days)
pools={k:[] for k in range(1,367) if k!=60}
bydoy={}
for b in baseDates: bydoy.setdefault(doy2(b),[]).append(b)
for k in pools:
    ds_=set()
    for b in bydoy.get(k,[]):
        for off in range(-5,6): ds_.add(b+dt.timedelta(off))
    pools[k]=sorted(i for i in (idx[t] for t in ds_ if t in idx))
    # check all days present
    assert all((b+dt.timedelta(o)) in idx for b in bydoy.get(k,[]) for o in range(-5,6)), k
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
import warnings; warnings.filterwarnings('ignore')
for k in pools:
    P=A[pools[k]]  # n,60,60
    thr[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(X):
    Y=np.full_like(X,np.nan)
    for dday in range(1,367):
        ids=[((dday-1+o)%366)+1 for o in range(-15,16)]
        Y[dday]=np.mean(X[ids],axis=0)
    return Y
T=smooth(thr[1:367].reshape(366,-1).reshape(366,60,60) if False else np.concatenate([thr[:1],thr[1:]])) if False else None
# smooth 366-array indexed 1..366 -> store at positions 0..365
def smooth366(X3):  # X3 shape (367,60,60), use indices 1..366
    arr=X3[1:367]
    out=np.empty_like(arr)
    for i in range(366):
        ids=[((i+o)%366) for o in range(-15,16)]
        out[i]=np.mean(arr[ids],axis=0)
    res=np.full_like(X3,np.nan); res[1:367]=out; return res
thrS=smooth366(thr); climS=smooth366(clim)
print(np.isnan(thrS[1:367]).sum(), np.nanmean(thrS[1:367]), np.nanmean(climS[1:367]))