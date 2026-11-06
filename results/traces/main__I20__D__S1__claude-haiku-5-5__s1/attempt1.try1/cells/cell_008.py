import fsspec, time, os, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
os.makedirs('/work/s',exist_ok=True)
t=time.time()
fs.get(base+'sst_20120601.nc','/work/s/t.nc')
print(time.time()-t, os.path.getsize('/work/s/t.nc'))
ds=xr.open_dataset('/work/s/t.nc',engine='h5netcdf')
print(ds.analysed_sst.attrs, ds.analysed_sst.encoding)
print(ds.time.values, ds.latitude.size, ds.longitude.size)