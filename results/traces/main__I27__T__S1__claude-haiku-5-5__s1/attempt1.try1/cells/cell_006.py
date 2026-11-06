import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/'
with fs.open(B+'sst_20080601.nc','rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf').load()
print(ds)
print(ds.lat.values[:5], ds.lon.values[:5])