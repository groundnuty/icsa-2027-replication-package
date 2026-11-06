
import xarray as xr, numpy as np, pandas as pd, time, os, json
os.makedirs('/tmp/w',exist_ok=True); os.makedirs('/workspace/output',exist_ok=True) if False else None
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lo=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
sub=ds.analysed_sst.isel(latitude=la,longitude=lo)
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2021-06-01','2021-08-31')).load()
np.savez('/tmp/w/cache.npz', b=b.values, bt=b.time.values.astype('datetime64[D]'), t=t.values, tt=t.time.values.astype('datetime64[D]'),
         lat=b.latitude.values, lon=b.longitude.values)
bt=pd.DatetimeIndex(b.time.values); tt=pd.DatetimeIndex(t.time.values)
bv=b.values.astype(np.float64); tv=t.values.astype(np.float64)
print(bt[0],bt[-1],len(bt), bt.is_unique, tt[0],tt[-1],len(tt))
sea=np.isfinite(tv).all(axis=0)
print('sea cells',sea.sum(),'of',sea.size,'all-nan baseline cells',(~np.isfinite(bv).any(axis=0)).sum())
print('target nan per cell min/max', np.isnan(tv).sum(axis=0).min(), np.isnan(tv).sum(axis=0).max())
print('baseline nan frac', np.isnan(bv).mean(), 'sea cells baseline partially nan', (np.isnan(bv).any(axis=0)&sea).sum())
