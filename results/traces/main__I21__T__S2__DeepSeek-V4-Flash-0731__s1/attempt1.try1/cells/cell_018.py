
import numpy as np
import xarray as xr
import pandas as pd

target_data = xr.open_dataset('target_data.nc')
target_time = target_data.time.values

diffs = np.diff(target_time.astype('datetime64[D]').astype(np.int64))
print(f"Unique time diffs: {np.unique(diffs)}")
print(f"Number of days: {len(target_time)}")

# Also check that the full dataset time coverage starts from 1982
# Let me check what the full time range of the dataset is
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print(f"Full time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Full time count: {len(ds.time.values)}")

# Check: do we need days before 1991-12-27 that might be within ±5 days of Jan 1 1992?
# Jan 1 1992 day-of-year = 1. The ±5 day window extends back to Dec 27 1991.
# Our baseline data starts at 1991-12-27. ✓

# Check: do we need days after 2002-12-31?
# Dec 31 2002 day-of-year = 366. The ±5 day window extends forward to Jan 5 2003.
# Our baseline data ends at 2003-01-05. ✓
