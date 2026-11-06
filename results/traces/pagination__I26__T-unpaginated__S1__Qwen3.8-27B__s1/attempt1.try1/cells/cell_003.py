import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(base + '/sst_20070601.nc', "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print(ds)
f.close()
