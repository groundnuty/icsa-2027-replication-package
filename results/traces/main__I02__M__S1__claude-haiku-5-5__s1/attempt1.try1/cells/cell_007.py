
import numpy as np, datetime as dt, json, os, warnings
import xarray as xr
warnings.filterwarnings('ignore')
d='/data/icsa2027_data_20261101T090944Z/s1z'
z=np.load('/tmp/sub.npz'); A=z['A']; days=[dt.date.fromisoformat(s) for s in z['days']]; LAT=z['lat']; LON=z['lon']
for dd in [days[0],days[500],days[-1]]:
    with xr.open_dataset(f"{d}/sst_{dd:%Y%m%d}.nc",engine='h5netcdf') as x:
        assert str(x.time.values[0])[:10]==dd.isoformat(), (dd,x.time.values)
def doy2(t):
    if t.month==2 and t.day==29: return 60
    return (dt.date(2001,t.month,t.day)-dt.date(2001,1,1)).days+1
print(doy2(dt.date(2004,2,28)),doy2(dt.date(2004,3,1)),doy2(dt.date(2004,12,31)),doy2(dt.date(2004,6,1)))
idx={t:i for i,t in enumerate(days)}
baseDates=[]; s=dt.date(1992,1,1)
while s<=dt.date(2002,12,31): baseDates.append(s); s+=dt.timedelta(1)
bydoy={}
for b in baseDates: bydoy.setdefault(doy2(b),[]).append(b)
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
pool_sizes=[]
for k in range(1,367):
    if k==60: continue
    ds_=set()
    for b in bydoy.get(k,[]):
        for off in range(-5,6): ds_.add(b+dt.timedelta(off))
    ids=sorted(idx[t] for t in ds_ if t in idx)
    pool_sizes.append(len(ids))
    P=A[ids]
    thr[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(P,axis=0)
print('pool sizes', min(pool_sizes), max(pool_sizes))
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth366(X3):
    arr=X3[1:367]; out=np.empty_like(arr)
    for i in range(366):
        ids=[(i+o)%366 for o in range(-15,16)]
        out[i]=np.mean(arr[ids],axis=0)
    res=np.full_like(X3,np.nan); res[1:367]=out; return res
thrS=smooth366(thr); climS=smooth366(clim)
print(np.isnan(thrS[1:367]).sum(), np.nanmean(thrS[1:367]))