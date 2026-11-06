
import numpy as np
import pickle
from datetime import date, timedelta

# Load saved data
baseline_data = np.load('/tmp/baseline_data.npy')
with open('/tmp/dates.pkl', 'rb') as f:
    dates = pickle.load(f)
baseline_dates = dates['baseline_dates']

def doy_from_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month - 1] + d.day

# Map each baseline date to its index
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Build baseline date lists by DOY (only for baseline years 1992-2002)
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
doy_to_baseline_dates = {}
d = baseline_start
while d <= baseline_end:
    doy = doy_from_date(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

# For each DOY (except 60), build the pool of date indices
doy_to_pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for bd in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            dd = bd + timedelta(days=offset)
            if dd in date_to_idx:
                pool_dates.add(date_to_idx[dd])
    doy_to_pool_indices[doy] = sorted(pool_dates)

# Compute threshold and climatology for each cell and DOY
n_lat, n_lon = 60, 60
n_doy = 366

# Initialize arrays
threshold = np.zeros((n_lat, n_lon, n_doy), dtype=np.float64)
climatology = np.zeros((n_lat, n_lon, n_doy), dtype=np.float64)

print("Computing thresholds and climatologies...")
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_idx = doy_to_pool_indices[doy]
    # For each cell
    for i in range(n_lat):
        for j in range(n_lon):
            vals = baseline_data[pool_idx, i, j]
            vals = vals[~np.isnan(vals)]
            if len(vals) == 0:
                threshold[i, j, doy-1] = np.nan
                climatology[i, j, doy-1] = np.nan
            else:
                threshold[i, j, doy-1] = np.quantile(vals, 0.9, method='hazen')
                climatology[i, j, doy-1] = np.mean(vals)
    if doy % 50 == 0:
        print(f"  Processed DOY {doy}")

print("Done computing per-DOY values")

# Set day 60 (index 59) to mean of days 59 and 61
threshold[:, :, 59] = (threshold[:, :, 58] + threshold[:, :, 60]) / 2
climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2

print("Day 60 set to mean of days 59 and 61")
print(f"Threshold shape: {threshold.shape}")
print(f"Climatology shape: {climatology.shape}")

# Save intermediate results
np.save('/tmp/threshold_unsmoothed.npy', threshold)
np.save('/tmp/climatology_unsmoothed.npy', climatology)
print("Saved unsmoothed thresholds and climatologies")
