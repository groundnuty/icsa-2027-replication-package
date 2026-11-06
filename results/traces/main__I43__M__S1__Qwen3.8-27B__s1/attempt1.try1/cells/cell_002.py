import xarray as xr, numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20170701.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
ds.close()
