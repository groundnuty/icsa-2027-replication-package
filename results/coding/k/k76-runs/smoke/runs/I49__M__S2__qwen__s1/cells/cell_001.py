import xarray as xr
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc", engine="h5netcdf", decode_times=False)
print(dict(ds.sizes))
ds.close()
