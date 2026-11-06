
import xarray as xr, numpy as np, pandas as pd, json
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lo=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
sub = ds.analysed_sst.isel(latitude=la, longitude=lo).sel(time=slice('1991-12-27','2021-08-31')).load()
T = pd.DatetimeIndex(sub.time.values.astype('datetime64[D]'))
A = sub.values.astype(np.float64)
print(A.shape, T[0], T[-1], np.isnan(A).sum(), np.nanmin(A), np.nanmax(A))
print(np.unique(np.diff(T.values)))
print(lat[la][[0,-1]], lon[lo][[0,-1]])
