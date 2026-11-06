
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check time resolution
print(ds.time.values[:5])
print(ds.time.values[-5:])
# check if daily
times = ds.time.values
diffs = np.diff(times.astype('datetime64[D]').astype(int))
print("Unique diffs:", np.unique(diffs))
