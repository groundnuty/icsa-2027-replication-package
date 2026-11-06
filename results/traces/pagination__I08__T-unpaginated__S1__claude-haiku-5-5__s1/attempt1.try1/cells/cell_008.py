import numpy as np, pandas as pd, json, os, xarray as xr
Z=np.load('/tmp/x/cache.npz'); arr=Z['arr']; la=Z['la']; lo=Z['lo']; dates=pd.to_datetime(Z['dates'])
nb=len(pd.date_range('1991-12-27','2003-01-05'))
alld=dates
# day-of-year mapping by month/day
def doy_of(ts):
    if ts.month==2 and ts.day==29: return 60
    d=pd.Timestamp(2001, ts.month, ts.day)  # non-leap calendar
    doy=d.dayofyear
    if doy>=60: doy+=1  # Mar 1 onward -> 61.. (2001 non-leap: Mar1 doy=60)
    return doy
# baseline/all dates in arr
ndays=len(alld)
doys=np.array([doy_of(t) for t in alld])
# sanity
assert doy_of(pd.Timestamp('2004-02-29'))==60 and doy_of(pd.Timestamp('2004-03-01'))==61 and doy_of(pd.Timestamp('2004-12-31'))==366 and doy_of(pd.Timestamp('2004-02-28'))==59
base_mask=(alld>=pd.Timestamp('1992-01-01'))&(alld<=pd.Timestamp('2002-12-31'))
ncell=arr.shape[1]*arr.shape[2]
flat=arr.reshape(ndays,-1)
thr=np.full((367,ncell),np.nan); clim=np.full((367,ncell),np.nan)
bdates=alld[base_mask]
# for each doy d != 60, pool = dates within +-5 days of some baseline date with doy d
for d in range(1,367):
    if d==60: continue
    bd=bdates[np.array([doy_of(t)==d for t in bdates])]
    if len(bd)==0: continue
    sel=np.zeros(ndays,bool)
    for b in bd:
        sel |= (alld>=b-pd.Timedelta(days=5))&(alld<=b+pd.Timedelta(days=5))
    pool=flat[sel]  # (n, ncell)
    with np.errstate(all='ignore'):
        thr[d]=np.array([np.nan if np.all(np.isnan(pool[:,c])) else np.quantile(pool[~np.isnan(pool[:,c]),c],0.9,method='hazen') for c in range(ncell)])
        clim[d]=np.nanmean(pool,axis=0)
print('windows ok', sel.sum())
