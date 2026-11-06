
import fsspec, os, xarray as xr, numpy as np
os.makedirs('/work',exist_ok=True); os.makedirs('output',exist_ok=True)
fs = fsspec.filesystem('onedata')
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','/work/sst_s2.nc')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
