
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values  # shape (4028, 60, 60)
print("Baseline SST shape:", baseline_sst.shape)

# Day of year mapping
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

all_dates_np = baseline_data.time.values.astype('datetime64[D]')
all_date_objs = [pd.Timestamp(t).date() for t in all_dates_np]

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

baseline_date_objs = [d for d in all_date_objs if baseline_start <= d <= baseline_end]

doy_to_baseline_dates = defaultdict(list)
for d in baseline_date_objs:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)

date_to_idx = {d: i for i, d in enumerate(all_date_objs)}

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

n_cells_lat = baseline_sst.shape[1]
n_cells_lon = baseline_sst.shape[2]

# Use 367 to have indices 0-366
thresholds = np.zeros((367, n_cells_lat, n_cells_lon), dtype=np.float64)
climatology = np.zeros((367, n_cells_lat, n_cells_lon), dtype=np.float64)

# Compute thresholds and climatology for each day of year
for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = doy_to_date_indices[doy]
    pool = baseline_sst[idxs, :, :].astype(np.float64)
    
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

print("Computed raw thresholds and climatology")

# Set day 60 = mean of days 59 and 61
thresholds[60] = (thresholds[59] + thresholds[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0

# Smoothing function
def smooth_wrap(arr, window=31, days_per_year=366):
    data = arr[1:367].copy()
    half = window // 2  # 15
    n = days_per_year
    result = np.zeros_like(data, dtype=np.float64)
    
    for d in range(n):
        total = np.zeros(data.shape[1:], dtype=np.float64)
        count = np.zeros(data.shape[1:], dtype=np.float64)
        for k in range(d - half, d + half + 1):
            idx = k % n
            vals = data[idx]
            mask = ~np.isnan(vals)
            total[mask] += vals[mask]
            count[mask] += 1
        result[d] = total / np.maximum(count, 1)
    
    smoothed = np.zeros_like(arr, dtype=np.float64)
    smoothed[1:367] = result
    return smoothed

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed. Sample values:")
print("Threshold DOY 1, cell (0,0):", thresholds_smooth[1, 0, 0])
print("Threshold DOY 60, cell (0,0):", thresholds_smooth[60, 0, 0])
print("Climatology DOY 1, cell (0,0):", climatology_smooth[1, 0, 0])

# Save results
np.save('thresholds_smooth.npy', thresholds_smooth)
np.save('climatology_smooth.npy', climatology_smooth)
print("Saved smoothed arrays")
