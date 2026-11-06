import xarray as xr
ds = xr.open_dataset("/data/icsa2027_data_20261101T090944Z/s1z/sst_20040701.nc", engine="h5netcdf")
print(ds)
print("---")
for name, v in ds.variables.items():
    print(name, v.dims, v.dtype, v.attrs if hasattr(v,'attrs') else "")
