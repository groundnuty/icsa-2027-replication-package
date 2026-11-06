import fsspec, xarray as xr, re, collections
fs = fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z/'
ds=xr.open_dataset(fs.open(d+'sst_19820101.nc','rb'),engine='h5netcdf')
print(ds)
