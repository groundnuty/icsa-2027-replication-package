
import fsspec, xarray as xr, numpy as np, pandas as pd, json, os
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=56.09)&(lat<=57.29))[0]; lo=np.where((lon>=10.55)&(lon<=11.75))[0]
sub = ds.analysed_sst.isel(latitude=slice(la[0],la[-1]+1), longitude=slice(lo[0],lo[-1]+1))
sub = sub.sel(time=slice('1991-12-27','2009-08-31')).load()
t = pd.DatetimeIndex(sub.time.values)
print(t[0], t[-1], len(t), (pd.Timestamp('2009-08-31')-pd.Timestamp('1991-12-27')).days+1, t.is_monotonic_increasing, t.has_duplicates)
print(t.to_series().diff().value_counts().head())
print(sub.latitude.values[:3], sub.longitude.values[:3])
