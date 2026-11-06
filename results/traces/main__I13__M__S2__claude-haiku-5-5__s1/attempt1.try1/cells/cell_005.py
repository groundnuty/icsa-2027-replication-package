
import xarray as xr, numpy as np, pandas as pd, os, json
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
sub=ds.sel(latitude=slice(56.09,57.29), longitude=slice(10.55,11.75))
b0,b1=pd.Timestamp('1991-12-27'),pd.Timestamp('2003-01-05')
bsel=sub.analysed_sst.sel(time=slice(b0,b1))
base=bsel.load().values.astype(np.float64)
btime=pd.DatetimeIndex(bsel.time.values)
tsel=sub.analysed_sst.sel(time=slice('2021-06-01','2021-08-31'))
tgt=tsel.load().values.astype(np.float64)
ttime=pd.DatetimeIndex(tsel.time.values)
print(base.shape,tgt.shape, btime[0],btime[-1], ttime[0],ttime[-1])
cum=[0,31,60,91,121,152,182,213,244,274,305,335]
def doy(t): return cum[t.month-1]+t.day
bd=[t for t in btime if pd.Timestamp('1992-01-01')<=t<=pd.Timestamp('2002-12-31')]
print(len(bd), doy(pd.Timestamp('2021-03-01')), doy(pd.Timestamp('2021-02-28')))
idx={t:i for i,t in enumerate(btime)}
ny,nx=base.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
pools={}
for d in range(1,367):
    if d==60: continue
    dates=set()
    for b in bd:
        if doy(b)==d:
            for k in range(-5,6): dates.add(b+pd.Timedelta(days=k))
    dates=sorted(t for t in dates if t in idx)
    pool=base[[idx[t] for t in dates]]
    pools[d]=len(dates)
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
thr=thr[1:367]; clim=clim[1:367]
def smooth(a):
    out=np.empty_like(a)
    for d in range(366):
        ii=[(d+k)%366 for k in range(-15,16)]
        out[d]=a[ii].mean(axis=0)
    return out
thrS=smooth(thr)
print(pools[1],pools[59],pools[61],pools[100])
sea=np.all(np.isfinite(tgt),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'nan in thr at sea', np.isnan(thrS[:,sea]).sum())
