import xarray as xr
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds)
print("\n--- coords ---")
for c in ds.coords:
    v = ds[c]
    print(c, v.dims, v.dtype, v.shape, v.values[:3] if v.ndim==1 else "")
print("\n--- data vars ---")
for v in ds.data_vars:
    print(v, ds[v].dims, ds[v].dtype, ds[v].shape)
