
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import fsspec
import xarray as xr

def day_of_year(month, day):
    """Map month and day to day of year 1-366 using fixed mapping."""
    month_start = {
        1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153,
        7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336,
    }
    return month_start[month] + day - 1

def dt_to_pydatetime(np_dt):
    return np_dt.astype('datetime64[us]').astype(datetime)

# Load data
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
times = ds.time.values

lat_idx = slice(330, 390)
lon_idx = slice(551, 611)

# Extended baseline: indices 3647 to 7674 inclusive
baseline_data = ds['analysed_sst'].isel(time=slice(3647, 7675),
                                         latitude=lat_idx, longitude=lon_idx).values
baseline_times = times[3647:7675]

# Target: indices 7821 to 7912 inclusive
target_data = ds['analysed_sst'].isel(time=slice(7821, 7913),
                                       latitude=lat_idx, longitude=lon_idx).values
target_times = times[7821:7913]

# Convert to Python datetimes
baseline_pydates = [dt_to_pydatetime(t) for t in baseline_times]
target_pydates = [dt_to_pydatetime(t) for t in target_times]

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")

# Compute day of year for each baseline date
baseline_doy = np.array([day_of_year(d.month, d.day) for d in baseline_pydates])

# Identify baseline dates (1992-01-01 to 2002-12-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_in_range = np.array([(d >= baseline_start and d <= baseline_end) for d in baseline_pydates])
print(f"Number of baseline dates in range: {baseline_in_range.sum()}")

# Build pools: for each doy d, list of indices in baseline_data that belong to pool d
pool_indices = defaultdict(list)

for i, t0 in enumerate(baseline_pydates):
    if not baseline_in_range[i]:
        continue
    d = baseline_doy[i]
    if d == 60:
        continue  # Day 60 gets no pool of its own
    t_start = t0 - timedelta(days=5)
    t_end = t0 + timedelta(days=5)
    # Scan all dates in extended baseline
    for j, t in enumerate(baseline_pydates):
        if t_start <= t <= t_end:
            pool_indices[d].append(j)

# Deduplicate indices for each pool
for d in pool_indices:
    pool_indices[d] = sorted(set(pool_indices[d]))

print(f"Number of pools: {len(pool_indices)}")
# Check sizes for a few
for d in [1, 59, 61, 153, 366]:
    n = len(pool_indices[d])
    print(f"Pool for doy {d}: {n} dates")
