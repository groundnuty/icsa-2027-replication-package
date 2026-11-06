import xarray as xr
import fsspec
import os

fs = fsspec.filesystem('onedata')
remote_file = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_file = '/work/sst_s2.nc'
fs.get(remote_file, local_file)

with xr.open_dataset(local_file, engine="h5netcdf") as ds:
    print(ds)
    print(f"Time range: {ds.time.min().values} to {ds.time.max().values}")

# Let's check if the dataset contains the required range
# Target period: 2012-06-01 to 2012-08-31
# Baseline period: 1992-01-01 to 2002-12-31 (plus buffers)
