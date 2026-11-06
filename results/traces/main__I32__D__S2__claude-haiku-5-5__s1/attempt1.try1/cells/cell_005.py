
import xarray as xr, numpy as np, pandas as pd, json
ds = xr.open_dataset('/work/sst.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=59.05)&(lat<=60.25))[0]; lo=np.where((lon>=21.25)&(lon<=22.45))[0]
sub = ds.analysed_sst.sel(time=slice('1991-12-27','2005-08-31')).isel(latitude=la, longitude=lo).load()
A = sub.values.astype(np.float64); t = pd.DatetimeIndex(sub.time.values)
tgt = (t>=pd.Timestamp('2005-06-01'))&(t<=pd.Timestamp('2005-08-31'))
print(A.shape, tgt.sum(), np.isnan(A[tgt]).any(axis=0).sum(), (~np.isnan(A[tgt]).any(axis=0)).sum(), np.isnan(A).all(axis=0).sum())
print(np.nanmin(A), np.nanmax(A))
