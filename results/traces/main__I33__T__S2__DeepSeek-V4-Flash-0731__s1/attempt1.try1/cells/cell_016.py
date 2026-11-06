
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict
import time

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

# Get baseline SST values as numpy array
baseline_sst = baseline_data.analysed_sst.values  # shape (4028, 60, 60)
print("Baseline SST shape:", baseline_sst.shape, "dtype:", baseline_sst.dtype)

# Day of year mapping
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

# All dates in the baseline dataset
all_dates_np = baseline_data.time.values.astype('datetime64[D]')
all_date_objs = [pd.Timestamp(t).date() for t in all_dates_np]

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# Baseline dates
baseline_date_objs = [d for d in all_date_objs if baseline_start <= d <= baseline_end]

# Group baseline dates by day of year
doy_to_baseline_dates = defaultdict(list)
for d in baseline_date_objs:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)

# Build date-to-index map
date_to_idx = {d: i for i, d in enumerate(all_date_objs)}

# For each day of year, collect the date indices in its pool
doy_to_date_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = set()
    for b in doy_to_baseline_dates.get(doy, []):
        for delta in range(-5, 6):
            t = b + timedelta(days=delta)
            if t in date_to_idx:
                pool_indices.add(date_to_idx[t])
    doy_to_date_indices[doy] = sorted(pool_indices)

print("Built doy_to_date_indices")

# Compute threshold and climatology for each cell
n_cells_lat = baseline_sst.shape[1]
n_cells_lon = baseline_sst.shape[2]
n_cells = n_cells_lat * n_cells_lon

# Initialize arrays
thresholds = np.zeros((366, n_cells_lat, n_cells_lon), dtype=np.float64)
climatology = np.zeros((366, n_cells_lat, n_cells_lon), dtype=np.float64)

# For each day of year, compute threshold and climatology for all cells
for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = doy_to_date_indices[doy]
    pool = baseline_sst[idxs, :, :].astype(np.float64)  # shape (n_pool, 60, 60)
    
    # Compute threshold (90th percentile, method="hazen") and mean for each cell
    # For each cell, gather the pool values, ignore NaN
    for i in range(n_cells_lat):
        for j in range(n_cells_lon):
            vals = pool[:, i, j]
            vals_clean = vals[~np.isnan(vals)]
            if len(vals_clean) > 0:
                thresholds[doy, i, j] = np.percentile(vals_clean, 90, method='hazen')
                climatology[doy, i, j] = np.mean(vals_clean)
            else:
                thresholds[doy, i, j] = np.nan
                climatology[doy, i, j] = np.nan

print("Computed thresholds and climatology for all days of year")
print("Sample threshold for DOY 1, cell (0,0):", thresholds[0, 0, 0])
print("Sample climatology for DOY 1, cell (0,0):", climatology[0, 0, 0])
