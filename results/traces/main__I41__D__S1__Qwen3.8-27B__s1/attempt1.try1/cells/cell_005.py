import fsspec, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
fs.get(base + '/sst_20210601.nc', '/work/data/sst_20210601.nc')
import xarray as xr
ds = xr.open_dataset('/work/data/sst_20210601.nc', engine='h5netcdf')
print(ds)
