import fsspec, time, numpy as np, xarray as xr, os
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
ds = xr.open_dataset('/work/d/first.nc', engine='h5netcdf')
lat = ds.latitude.values.astype(float); lon = ds.longitude.values.astype(float)
la = np.where((lat>=57.13-1e-6)&(lat<=58.33+1e-6))[0]; lo = np.where((lon>=22.79-1e-6)&(lon<=23.99+1e-6))[0]
print(la.min(), la.max(), len(la), lo.min(), lo.max(), len(lo))
print(lat[la[[0,-1]]], lon[lo[[0,-1]]])
t=time.time(); fs.get(base+'sst_20100601.nc','/work/d/t.nc'); print(time.time()-t, os.path.getsize('/work/d/t.nc'))