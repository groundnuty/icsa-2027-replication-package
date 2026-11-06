import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd
from collections import defaultdict

# Load data
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')
base_sst = base_ds['analysed_sst'].values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
base_time = base_ds['time'].values
target_time = target_ds['time'].values

base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)
baseline_dates_by_doy = defaultdict(list)
for date in base_dates:
    if baseline_start <= date <= baseline_end:
        d = day_of_year(date)
        baseline_dates_by_doy[d].append(date)

date_to_idx = {d: i for i, d in enumerate(base_dates)}

pool_indices = defaultdict(set)
for d, dates in baseline_dates_by_doy.items():
    if d == 60:
        continue
    for b in dates:
        for delta in range(-5, 6):
            t = b + dt.timedelta(days=delta)
            if t in date_to_idx:
                pool_indices[d].add(date_to_idx[t])

sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum())

n_lat, n_lon = 60, 60

# Arrays indexed by DOY 1-366 (use size 367, index 0 unused)
threshold = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

# Compute for each DOY (except 60)
for d in range(1, 367):
    if d == 60:
        continue
    idxs = sorted(pool_indices[d])
    if not idxs:
        print(f"Warning: no pool for DOY {d}")
        continue
    pool_sst = base_sst[idxs, :, :]
    
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_sst[:, i, j]
            vals = vals[np.isfinite(vals)]
            if len(vals) == 0:
                continue
            threshold[d, i, j] = np.quantile(vals, 0.9, method='hazen')
            climatology[d, i, j] = np.mean(vals)

# Day 60: mean of days 59 and 61
threshold[60, :, :] = (threshold[59, :, :] + threshold[61, :, :]) / 2.0
climatology[60, :, :] = (climatology[59, :, :] + climatology[61, :, :]) / 2.0

# Verify: check if any threshold values are NaN for sea cells
nan_count = np.sum(~np.isfinite(threshold[1:367, sea_mask]))
print("NaN in threshold for sea cells:", nan_count)
nan_count_c = np.sum(~np.isfinite(climatology[1:367, sea_mask]))
print("NaN in climatology for sea cells:", nan_count_c)

# Check some values
print("Threshold[60, 0, 0]:", threshold[60, 0, 0])
print("Threshold[59, 0, 0]:", threshold[59, 0, 0])
print("Threshold[61, 0, 0]:", threshold[61, 0, 0])
print("Mean of 59 and 61:", (threshold[59, 0, 0] + threshold[61, 0, 0]) / 2)

# Save intermediate results
np.save('/tmp/threshold_raw.npy', threshold)
np.save('/tmp/climatology_raw.npy', climatology)
np.save('/tmp/sea_mask.npy', sea_mask)
print("Saved intermediate results")
