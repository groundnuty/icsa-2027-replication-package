import fsspec
import os
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
p = f"{base}/sst_20090601.nc"
fs.get(p, '/work/data/sst_20090601.nc')
print(os.path.getsize('/work/data/sst_20090601.nc'))
import xarray as xr
ds = xr.open_dataset('/work/data/sst_20090601.nc', engine="h5netcdf")
print(ds)
ds.close()
