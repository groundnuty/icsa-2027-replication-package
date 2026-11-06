
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import pandas as pd

# Load data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values
baseline_time = baseline_data.time.values
target_sst = target_data.analysed_sst.values
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
baseline_sst_f64 = baseline_sst.astype(np.float64)

# Arrays indexed by day-of-year 1-366 -> index 0-365
threshold_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

print("Computing thresholds and climatology...")

for d in range(1, 367):
    if d == 60:
        continue
    idx = doy_to_indices[d]
    pool_values = baseline_sst_f64[idx, :, :]
    
    for la, lo in sea_indices:
        vals = pool_values[:, la, lo]
        vals_clean = vals[np.isfinite(vals)]
        if len(vals_clean) == 0:
            continue
        threshold_raw[d-1, la, lo] = np.percentile(vals_clean, 90, method='hazen')
        climatology_raw[d-1, la, lo] = np.mean(vals_clean)

print("Done computing raw thresholds and climatology.")

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
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

# Now apply the 31-day centered moving mean that wraps around the year
# For day d (1-366), average days d-15 to d+15 (modulo 366, 1-indexed)
print("Applying smoothing...")

threshold_smooth = np.full_like(threshold_raw, np.nan)
climatology_smooth = np.full_like(climatology_raw, np.nan)

for d in range(1, 367):  # day-of-year 1 to 366
    d_idx = d - 1  # 0-indexed
    # Window: d-15 to d+15, wrapping modulo 366 (1-indexed)
    window = [(d + k - 1) % 366 for k in range(-15, 16)]  # 0-indexed
    for la, lo in sea_indices:
        vals_t = threshold_raw[window, la, lo]
        vals_c = climatology_raw[window, la, lo]
        threshold_smooth[d_idx, la, lo] = np.mean(vals_t[np.isfinite(vals_t)])
        climatology_smooth[d_idx, la, lo] = np.mean(vals_c[np.isfinite(vals_c)])

print("Done smoothing.")
print(f"NaN in threshold_smooth for sea cells: {np.sum(~np.isfinite(threshold_smooth[:, sea_cells]))}")
print(f"NaN in climatology_smooth for sea cells: {np.sum(~np.isfinite(climatology_smooth[:, sea_cells]))}")

# Save intermediate results
np.save('threshold_smooth.npy', threshold_smooth)
np.save('climatology_smooth.npy', climatology_smooth)
np.save('sea_cells.npy', sea_cells)

# Also save the raw data for later
print("Saved intermediate results.")
