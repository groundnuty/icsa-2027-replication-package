
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

# Identify sea cells
n_lat = baseline_sst.shape[1]
n_lon = baseline_sst.shape[2]
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for la in range(n_lat):
    for lo in range(n_lon):
        if np.all(np.isfinite(target_sst[:, la, lo])):
            sea_cells[la, lo] = True

sea_indices = np.argwhere(sea_cells)

# Compute threshold and climatology per sea cell per day-of-year
# Use float64
baseline_sst_f64 = baseline_sst.astype(np.float64)

threshold_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

print("Computing thresholds and climatology...")

# Process each day-of-year
for d in range(1, 367):
    if d == 60:
        continue
    idx = doy_to_indices[d]
    # Get the pool values for this day-of-year
    # pool_values shape: (len(idx), n_lat, n_lon)
    pool_values = baseline_sst_f64[idx, :, :]  # (n_pool, n_lat, n_lon)
    
    for la, lo in sea_indices:
        vals = pool_values[:, la, lo]
        # Remove NaN
        vals_clean = vals[np.isfinite(vals)]
        if len(vals_clean) == 0:
            continue
        # Threshold: 90th percentile using numpy method="hazen" (Hyndman-Fan type 5)
        threshold_raw[d, la, lo] = np.percentile(vals_clean, 90, method='hazen')
        # Climatology: mean
        climatology_raw[d, la, lo] = np.mean(vals_clean)

print("Done computing raw thresholds and climatology.")

# Set day 60 to mean of days 59 and 61
for la, lo in sea_indices:
    threshold_raw[59, la, lo] = (threshold_raw[58, la, lo] + threshold_raw[60, la, lo]) / 2.0
    climatology_raw[59, la, lo] = (climatology_raw[58, la, lo] + climatology_raw[60, la, lo]) / 2.0

# Check for NaN in sea cells after setting day 60
nan_count = 0
for la, lo in sea_indices:
    for d in range(366):
        if np.isnan(threshold_raw[d, la, lo]):
            nan_count += 1
print(f"NaN threshold values in sea cells: {nan_count}")
