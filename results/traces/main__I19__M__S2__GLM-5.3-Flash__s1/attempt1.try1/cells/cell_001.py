import xarray as xr, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
print("\ndims:", dict(ds.sizes))