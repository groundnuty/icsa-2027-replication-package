
import numpy as np, pandas as pd, json, os
z=np.load('/tmp/cache.npz',allow_pickle=True)
X=z['X']; dates=pd.DatetimeIndex(z['dates']); LAT=z['LAT']; LON=z['LON']
bl_mask=(dates<=pd.Timestamp('2003-01-05'))&(dates>=pd.Timestamp('1991-12-27'))
tg_mask=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
cum=[0,31,60,91,121,152,182,213,244,274,305,335]  # Feb=29 always
def doy(ts):
    return cum[ts.month-1]+ts.day
date_index={d:i for i,d in enumerate(dates)}
# baseline dates
bdates=pd.date_range('1992-01-01','2002-12-31')
pool_idx={d:set() for d in range(1,367)}
for b in bdates:
    d=doy(b)
    if d==60: continue
    for k in range(-5,6):
        dd=b+pd.Timedelta(days=k)
        pool_idx[d].add(date_index[dd])
ny,nx=LAT.size,LON.size
thr_raw=np.full((367,ny,nx),np.nan); clim_raw=np.full((367,ny,nx),np.nan)
sea_all=np.ones((ny,nx),bool)
Xs=X  # all loaded days
for d in range(1,367):
    if d==60: continue
    idx=sorted(pool_idx[d])
    P=Xs[idx]  # (n,ny,nx)
    thr_raw[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim_raw[d]=np.nanmean(P,axis=0)
    npool=len(idx)
print('pool size example d=1', len(pool_idx[1]), 'd=366', len(pool_idx[366]), 'd=59',len(pool_idx[59]))
# day 60 -> mean of 59 and 61; index arrays 1..366 -> use 0-based day array of 366
thr=np.full((366,ny,nx),np.nan); clim=np.full((366,ny,nx),np.nan)
thr[:]=thr_raw[1:]; clim[:]=clim_raw[1:]
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(A):
    out=np.empty_like(A)
    for d in range(366):
        ids=[(d+k)%366 for k in range(-15,16)]
        out[d]=A[ids].mean(axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
print('nan thresholds among sea cells', np.isnan(thr_s[:,LAT.size//2,:]).sum())
print('thr range', np.nanmin(thr_s), np.nanmax(thr_s), 'clim range', np.nanmin(clim_s), np.nanmax(clim_s))
