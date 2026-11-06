import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
with fs.open(P+'sst_20100601.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf').load()
print(d)
print(d.attrs)