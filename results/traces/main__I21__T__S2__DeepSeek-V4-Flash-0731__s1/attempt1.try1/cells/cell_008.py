
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import pandas as pd

# Load data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values  # (4028, 60, 60)
baseline_time = baseline_data.time.values
target_sst = target_data.analysed_sst.values  # (92, 60, 60)
target_time = target_data.time.values

baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

# Build day-of-year to pool indices mapping
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)

doy_to_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_indices = set()
    for i, dt in enumerate(baseline_dates):
        if base_start <= dt <= base_end and day_of_year(dt) == d:
            for j in range(max(0, i-5), min(len(baseline_dates), i+6)):
                pool_indices.add(j)
    doy_to_indices[d] = sorted(pool_indices)

# Compute threshold and climatology for each day-of-year, per sea cell
n_lat = baseline_sst.shape[1]
n_lon = baseline_sst.shape[2]

# First, identify sea cells: cells where SST is finite on every day of the target period
# target period: 2021-06-01 to 2021-08-31 (92 days)
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for la in range(n_lat):
    for lo in range(n_lon):
        if np.all(np.isfinite(target_sst[:, la, lo])):
            sea_cells[la, lo] = True

print(f"Sea cells: {np.sum(sea_cells)} out of {n_lat * n_lon}")
print(f"Land cells: {n_lat * n_lon - np.sum(sea_cells)}")

# Check which cells are sea vs land
sea_cell_coords = np.argwhere(sea_cells)
print(f"First few sea cells: {sea_cell_coords[:5]}")
