import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc'
with fs.open(p,'rb') as f:
    ds=xr.open_dataset(f,engine='h5netcdf').load()
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
