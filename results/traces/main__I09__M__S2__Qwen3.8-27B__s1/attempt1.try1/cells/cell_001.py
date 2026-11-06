import xarray as xr
import os

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
print(os.path.getsize(path))
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds)
ds.close()