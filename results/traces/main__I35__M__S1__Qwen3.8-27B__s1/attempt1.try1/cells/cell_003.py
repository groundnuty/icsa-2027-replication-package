import xarray as xr
base = "/data/icsa2027_data_20261101T090944Z/s1z"
ds = xr.open_dataset(base + "/sst_20090601.nc", engine="h5netcdf")
print(ds)
ds.close()
