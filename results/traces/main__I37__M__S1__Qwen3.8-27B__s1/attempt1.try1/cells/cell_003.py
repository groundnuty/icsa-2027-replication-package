import xarray as xr
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120701.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
print("---- attrs of variables ----")
for name, v in ds.variables.items():
    print(name, v.dims, v.dtype, dict(v.attrs) if hasattr(v,'attrs') else '')
