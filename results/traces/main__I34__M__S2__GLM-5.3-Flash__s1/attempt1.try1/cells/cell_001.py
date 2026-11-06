import xarray as xr, numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds)
print("\n--- encodings ---")
for v in list(ds.variables):
    print(v, dict(ds[v].encoding).get('dtype'), dict(ds[v].encoding).get('chunksizes'), dict(ds[v].encoding).get('_FillValue'))
