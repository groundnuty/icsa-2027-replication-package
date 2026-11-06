
import fsspec, os, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.81)&(lat<=56.01))[0]; lo=np.where((lon>=19.61)&(lon<=20.81))[0]
print(len(la),len(lo), lat[la[[0,-1]]], lon[lo[[0,-1]]])
t=ds.time.values
tb=(t>=np.datetime64('1991-12-27'))&(t<=np.datetime64('2003-01-05'))
tt=(t>=np.datetime64('2022-06-01'))&(t<=np.datetime64('2022-08-31'))
print(tb.sum(), tt.sum())
sub=ds.analysed_sst.isel(latitude=la,longitude=lo)
idx=np.where(tb|tt)[0]
A=sub.isel(time=idx).values.astype(np.float64)
tim=t[idx]
print(A.shape, np.isnan(A).mean())
