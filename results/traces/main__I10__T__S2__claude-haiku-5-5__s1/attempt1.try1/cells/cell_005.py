
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
v=ds.analysed_sst
t=time.time()
sub = v.isel(latitude=slice(109,169), longitude=slice(373,433), time=slice(0,50)).values
print(sub.shape, time.time()-t, np.isnan(sub).mean())
print(ds.time.values[:3], ds.time.values[-1])
