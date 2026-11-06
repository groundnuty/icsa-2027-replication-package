
import numpy as np, xarray as xr, pandas as pd, os, json
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=63.31-1e-6)&(lat<=64.51+1e-6))[0]; lo=np.where((lon>=21.31-1e-6)&(lon<=22.51+1e-6))[0]
sub=ds.analysed_sst.sel(time=slice('1991-12-27','2009-08-31')).isel(latitude=la,longitude=lo).load()
times = pd.DatetimeIndex(sub.time.values)
vals = sub.values.astype(np.float64)
def doy(ts):  # ts: DatetimeIndex; leap-calendar day of year: 29Feb=60, 31Dec=366
    return np.array([pd.Timestamp(2000,t.month,t.day).dayofyear for t in ts])
print(doy(pd.DatetimeIndex(['2001-03-01','2001-12-31','2001-02-28','2000-02-29'])))
tpos = {t:i for i,t in enumerate(times)}
base = pd.date_range('1992-01-01','2002-12-31')
pools = {d:[] for d in range(1,367) if d!=60}
bd = doy(base)
for b,d in zip(base,bd):
    if d==60: continue
    for k in range(-5,6):
        pools[d].append(tpos[b+pd.Timedelta(days=k)])
print(times[0], times[-1], len(times))
thr_raw=np.full((367,)+vals.shape[1:],np.nan); clim_raw=np.full_like(thr_raw,np.nan)
for d,idx in pools.items():
    P = vals[idx]  # (n,60,60)
    allnan = np.all(np.isnan(P),axis=0)
    with np.errstate(all='ignore'):
        thr_raw[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
        clim_raw[d]=np.nanmean(P,axis=0)
    thr_raw[d][allnan]=np.nan; clim_raw[d][allnan]=np.nan
thr=thr_raw[1:].copy(); clim=clim_raw[1:].copy()  # index 0..365 => doy 1..366
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        ii=[(d+k)%366 for k in range(-15,16)]
        out[d]=np.mean(a[ii],axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
print(np.isnan(thrS).sum(), np.isnan(climS).sum())
# target period
tgt = (times>=pd.Timestamp('2009-06-01'))&(times<=pd.Timestamp('2009-08-31'))
ti = np.where(tgt)[0]; ttimes=times[ti]
T = vals[ti]
finite_all = np.all(np.isfinite(T),axis=0)
print('target days',len(ti), 'sea cells',finite_all.sum(),'of',finite_all.size)
print('land/NaN fraction in target', 1-finite_all.mean())
