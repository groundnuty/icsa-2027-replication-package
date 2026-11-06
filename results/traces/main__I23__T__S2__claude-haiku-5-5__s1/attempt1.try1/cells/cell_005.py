
import fsspec, xarray as xr, numpy as np, pandas as pd
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v=ds.analysed_sst
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.41-1e-6)&(lat<=58.61+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
sub = v.isel(latitude=la, longitude=lo)
base = sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tgt = sub.sel(time=slice('2013-06-01','2013-08-31')).load()
print(base.shape, tgt.shape, base.time.values[[0,-1]], tgt.time.values[[0,-1]])
print(np.isnan(base.values).mean(), np.isnan(tgt.values).mean())
print(np.nanmin(tgt.values), np.nanmax(tgt.values))
