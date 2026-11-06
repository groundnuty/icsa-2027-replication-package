
import xarray as xr, numpy as np, pandas as pd
ds = xr.open_dataset('/work/sst.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=59.05)&(lat<=60.25))[0]; lo=np.where((lon>=21.25)&(lon<=22.45))[0]
sub = ds.analysed_sst.sel(time=slice('1991-12-27','2005-08-31')).isel(latitude=la, longitude=lo).load()
A = sub.values.astype(np.float64); t = pd.DatetimeIndex(sub.time.values)
nanc = np.isnan(A).sum(axis=0)
print(np.unique(nanc))
print(t[0], t[-1], len(t))
# check the calendar gaps in data
print(pd.Series(t).diff().value_counts().head())
