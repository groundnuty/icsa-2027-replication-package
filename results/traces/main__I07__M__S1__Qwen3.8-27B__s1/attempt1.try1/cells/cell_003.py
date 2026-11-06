import xarray as xr
base = "/data/icsa2027_data_20261101T090944Z/s1z"
p = base + "/sst_20210601.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
print("---- encodings ----")
for v in ds.variables:
    print(v, ds[v].dtype)
