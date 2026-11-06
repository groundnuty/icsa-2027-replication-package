import numpy as np, pandas as pd, datetime as _dt, json, os
import xarray as xr
Z=np.load('/tmp/w/sub.npz', allow_pickle=True)
sst=Z['sst']; dates=pd.to_datetime(Z['dates']); LAT=Z['lat']; LON=Z['lon']
t0=dates[0]
def idx(d): return int((pd.Timestamp(d)-t0).days)
# doy with leap calendar
doy_of=lambda ts: _dt.date(2000, ts.month, ts.day).timetuple().tm_yday
doys=np.array([doy_of(x) for x in dates])
base_mask=(dates>=pd.Timestamp('1992-01-01'))&(dates<=pd.Timestamp('2002-12-31'))
# baseline windows
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
sst64=sst.astype(np.float64)
for d in range(1,367):
    if d==60: continue
    bdates=dates[base_mask & (doys==d)]
    idxs=set()
    for b in bdates:
        for k in range(-5,6):
            idxs.add(idx(b+pd.Timedelta(days=k)))
    idxs=sorted(idxs)
    pool=sst64[idxs]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    with np.errstate(all='ignore'):
        clim[d]=np.nanmean(pool,axis=0)
    if d==59: print('pool size d=59', len(idxs))
# day 60 index 60 in 1-based -> array index 60
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    # a: (367,60,60), index 0 unused; days 1..366
    b=a[1:367]  # 366 days
    out=np.empty_like(b)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=b[ii].mean(axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print(np.isnan(thr_s[:, :, :]).sum(), np.isnan(thr_s[:, 0,0]).sum())
sea=np.isfinite(sst64[ (dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31')) ]).all(axis=0)
print('sea cells', sea.sum(), 'of', sea.size)
