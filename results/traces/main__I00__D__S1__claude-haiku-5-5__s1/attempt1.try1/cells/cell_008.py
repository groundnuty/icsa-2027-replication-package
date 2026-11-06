import fsspec, os, json, numpy as np, xarray as xr, pandas as pd
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2004-06-01','2004-08-31'))
def get(d):
    s=d.strftime('%Y%m%d'); loc=f'/work/d/sst_{s}.nc'
    if not os.path.exists(loc):
        fs.get(f'icsa2027_data_20261101T090944Z/s1z/sst_{s}.nc',loc)
    with xr.open_dataset(loc,engine='h5netcdf') as ds:
        lat=ds.latitude.values; lon=ds.longitude.values
        il=np.where((lat>=54.13-1e-4)&(lat<=55.33+1e-4))[0]
        jl=np.where((lon>=14.67-1e-4)&(lon<=15.87+1e-4))[0]
        v=ds.analysed_sst.isel(latitude=il,longitude=jl).values.astype(np.float64)
        return v, lat[il], lon[jl]
with ThreadPoolExecutor(8) as ex:
    res=list(ex.map(get,dates))
lat=res[0][1]; lon=res[0][2]
arr=np.stack([r[0][0] for r in res])  # (N,60,60)
N=len(dates)
dt=pd.DatetimeIndex(dates)
doy=np.array([pd.Timestamp(2000,m,d).dayofyear for m,d in zip(dt.month,dt.day)])
# baseline index bookkeeping
is_base_target = (dt>=pd.Timestamp('1992-01-01'))&(dt<=pd.Timestamp('2002-12-31'))
base_dates=dt[is_base_target]
pos={d:i for i,d in enumerate(dt)}
ny=arr.shape[1:]
thr=np.full((367,)+ny,np.nan); clim=np.full((367,)+ny,np.nan)
for d in range(1,367):
    if d==60: continue
    bsel=base_dates[doy[is_base_target]==d]
    if len(bsel)==0: continue
    idx=set()
    for b in bsel:
        for k in range(-5,6):
            idx.add(pos[b+pd.Timedelta(days=k)])
    idx=sorted(idx)
    pool=arr[idx]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.empty_like(a)
    days=np.arange(1,367)
    for i,d in enumerate(days):
        ids=[((d-1+k)%366) for k in range(-15,16)]
        out[d]=np.sum(a[[x+1 for x in ids]],axis=0)/31.0
    return out
thr_s=smooth(thr); clim_s=smooth(clim)
# sea cells: finite on all target days
tgt_idx=np.where(~is_base_target & (dt>=pd.Timestamp('2004-06-01')))[0]
tgt=arr[tgt_idx]; tgt_dt=dt[tgt_idx]; tgt_doy=doy[tgt_idx]
sea=np.all(np.isfinite(tgt),axis=0)
print('sea cells',sea.sum(),'of',sea.size, 'target days',len(tgt_idx), tgt_dt[0].date(), tgt_dt[-1].date())
print('thr nan at sea cells?', np.isnan(thr_s[1:][:,sea]).sum(), np.isnan(thr_s[tgt_doy][:,sea]).sum())
