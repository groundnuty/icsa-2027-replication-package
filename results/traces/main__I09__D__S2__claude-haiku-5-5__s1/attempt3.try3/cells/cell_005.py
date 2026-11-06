
import fsspec, os, xarray as xr, numpy as np, pandas as pd
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.81)&(lat<=56.01))[0]; lo=np.where((lon>=19.61)&(lon<=20.81))[0]
t=ds.time.values
tb=(t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-01-05'))
tt=(t>=np.datetime64('2022-06-01'))&(t<=np.datetime64('2022-08-31'))
idx=np.where(tb|tt)[0]
sub=ds.analysed_sst.isel(latitude=la,longitude=lo)
A=sub.isel(time=idx).values.astype(np.float64)
np.savez('/work/sub.npz', A=A, tim=t[idx].astype('datetime64[ns]').astype(np.int64), lat=lat[la], lon=lon[lo])
print(A.shape)
