
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Generate all dates in the full window
start = date(1991, 12, 27)
end = date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
all_dates = np.array(all_dates, dtype=object)
n_dates = len(all_dates)

base_start_d = date(1992, 1, 1)
base_end_d = date(2002, 12, 31)
base_mask = np.array([base_start_d <= x <= base_end_d for x in all_dates])

date_to_idx = {d: i for i, d in enumerate(all_dates)}

doy_to_base_dates = defaultdict(list)
for y in all_dates[base_mask]:
    d = day_of_year_custom(y)
    doy_to_base_dates[d].append(y)

doy_to_pool_mask = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_mask = np.zeros(n_dates, dtype=bool)
    for y in doy_to_base_dates[d]:
        y_idx = date_to_idx[y]
        lo = max(0, y_idx - 5)
        hi = min(n_dates, y_idx + 6)
        pool_mask[lo:hi] = True
    doy_to_pool_mask[d] = pool_mask

print("Pool masks computed.")

# Now let's load the data and compute thresholds/climatology
import xarray as xr
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_idx = slice(217, 277)
lon_idx = slice(421, 481)
base_start_idx = 3647
base_end_idx = 7674

base_sub = ds.analysed_sst.isel(time=slice(base_start_idx, base_end_idx+1),
                                 latitude=lat_idx, longitude=lon_idx)
base_data = base_sub.values  # (4028, 60, 60)
print(f"Base data shape: {base_data.shape}")

# Identify sea cells from target data
tgt_start_idx = 9282
tgt_end_idx = 9373
tgt_sub = ds.analysed_sst.isel(time=slice(tgt_start_idx, tgt_end_idx+1),
                                latitude=lat_idx, longitude=lon_idx)
tgt_data = tgt_sub.values  # (92, 60, 60)
print(f"Target data shape: {tgt_data.shape}")

# Sea cells: finite on all target days
sea_cells = ~np.isnan(tgt_data).any(axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Close dataset to free memory
ds.close()
