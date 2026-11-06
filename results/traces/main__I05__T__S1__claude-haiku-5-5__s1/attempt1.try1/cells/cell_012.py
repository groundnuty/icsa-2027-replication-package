
import numpy as np, pandas as pd, json, os, io, time
import fsspec, xarray as xr
from concurrent.futures import ThreadPoolExecutor
if os.path.exists('/tmp/cache.npz'):
    z=np.load('/tmp/cache.npz',allow_pickle=True)
    X=z['X']; dates=pd.DatetimeIndex(z['dates']); LAT=z['LAT']; LON=z['LON']
    print('from cache')
else:
    fs=fsspec.filesystem('onedata'); base='icsa2027_data_20261101T090944Z/s1z'
    dates=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2021-06-01','2021-08-31'))
    dates=pd.DatetimeIndex(sorted(set(dates)))
    def load(d):
        with fs.open(f"{base}/sst_{d:%Y%m%d}.nc",'rb') as f:
            ds=xr.open_dataset(io.BytesIO(f.read()),engine='h5netcdf'); ds.load()
        lat=ds.latitude.values; lon=ds.longitude.values
        m=(lat>=54.39)&(lat<=55.59); n=(lon>=18.25)&(lon<=19.45)
        arr=ds.analysed_sst.values[0][np.ix_(m,n)].astype(np.float64)
        ds.close(); return arr, lat[m].astype(np.float64), lon[n].astype(np.float64)
    with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,dates))
    X=np.stack([r[0] for r in res]); LAT=res[0][1]; LON=res[0][2]
    np.savez('/tmp/cache.npz',X=X,dates=dates.values,LAT=LAT,LON=LON)
    print('loaded fresh')
bl_mask=(dates<=pd.Timestamp('2003-01-05'))&(dates>=pd.Timestamp('1991-12-27'))
tg_mask=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
cum=[0,31,60,91,121,152,182,213,244,274,305,335]
def doy(ts): return cum[ts.month-1]+ts.day
date_index={d:i for i,d in enumerate(dates)}
pool_idx={d:set() for d in range(1,367)}
for b in pd.date_range('1992-01-01','2002-12-31'):
    d=doy(b)
    if d==60: continue
    for k in range(-5,6): pool_idx[d].add(date_index[b+pd.Timedelta(days=k)])
ny,nx=LAT.size,LON.size
thr_raw=np.full((367,ny,nx),np.nan); clim_raw=np.full((367,ny,nx),np.nan)
for d in range(1,367):
    if d==60: continue
    P=X[sorted(pool_idx[d])]
    with np.errstate(all='ignore'):
        thr_raw[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
        clim_raw[d]=np.nanmean(P,axis=0)
thr=thr_raw[1:].copy(); clim=clim_raw[1:].copy()
thr[59]=(thr[58]+thr[60])/2; clim[59]=(clim[58]+clim[60])/2
def smooth(A):
    out=np.empty_like(A)
    for d in range(366):
        out[d]=A[[(d+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
thr_s=smooth(thr)
Xt=X[tg_mask]; tdates=dates[tg_mask]; T=len(tdates)
sea=np.all(np.isfinite(Xt),axis=0)
doys=np.array([doy(t) for t in tdates])-1
hot=(Xt>=thr_s[doys])&sea[None]
def runs(b):
    d=np.diff(np.concatenate([[0],b.astype(np.int8),[0]]))
    return list(zip(np.where(d==1)[0],np.where(d==-1)[0]-1))
mhw=np.zeros((T,ny,nx),bool); n_ev=0
for i in range(ny):
    for j in range(nx):
        if not sea[i,j]: continue
        ev=[(s,e) for s,e in runs(hot[:,i,j]) if e-s+1>=5]
        if not ev: continue
        mg=[list(ev[0])]
        for s,e in ev[1:]:
            if s-mg[-1][1]-1<=2: mg[-1][1]=e
            else: mg.append([s,e])
        n_ev+=len(mg)
        for s,e in mg: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
reg=runs(active)
events=[{"onset":str(tdates[s].date()),"end":str(tdates[e].date())} for s,e in reg]
print('sea cells',sea.sum(),'per-cell events',n_ev,'cell-days',int(mhw.sum()),'active days',int(active.sum()))
print(events)
print('hot cell-days', int(hot.sum()))
os.makedirs('output',exist_ok=True)
import xarray as xr
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
    coords={'time':tdates.values,'lat':LAT,'lon':LON})
ds_out['mhw'].attrs={'long_name':'marine heatwave mask (per-cell)'}
ds_out.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8'}})
rep={"region":{"lat_min":54.39,"lat_max":55.59,"lon_min":18.25,"lon_max":19.45},
     "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
     "target_analysed":{"start":str(tdates[0].date()),"end":str(tdates[-1].date())},
     "events":events,"complete":True,
     "caveats":"Sea cells = 3309 of 3600 region cells (finite every target day); land/partial cells set to 0. Baseline thresholds/climatology from date-based +/-5-day windows (1991-12-27 to 2003-01-05 data). Event joining uses index gaps of <=2 days between qualifying per-cell MHWs (>=5 hot days). Regional events are runs of active days with no minimum duration. Analysis uses SST as stored (float32 decoded to float64)."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read()[:1500])
