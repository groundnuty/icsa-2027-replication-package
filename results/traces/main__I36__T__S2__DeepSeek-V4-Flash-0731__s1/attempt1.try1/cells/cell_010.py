
import numpy as np
from datetime import datetime, timedelta

def day_of_year(month, day):
    """Map month and day to day of year 1-366 using fixed mapping."""
    month_start = {
        1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153,
        7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336,
    }
    return month_start[month] + day - 1

# Baseline dates: 1992-01-01 to 2002-12-31
# Plus extended windows: 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05

# Let me figure out the time indices for the baseline
# Extended baseline in data: index 3647 (1991-12-27) to 7674 (2003-01-05)

# Let me verify the data times
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
times = ds.time.values

# Check specific indices
for i in [3647, 3652, 7669, 7674]:
    print(f"Index {i}: {times[i]}")

# Target: 2003-06-01 to 2003-08-31
target_start = 7821
target_end = 7912  # inclusive
print(f"Target start: {times[7821]}")
print(f"Target end: {times[7912]}")
print(f"Target count: {7912 - 7821 + 1}")
