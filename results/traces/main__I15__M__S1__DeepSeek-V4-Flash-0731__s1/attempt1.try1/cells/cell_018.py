import numpy as np
from datetime import datetime, timedelta
import pickle

# Load data
base_sst_sea = np.load('/tmp/base_sst_sea.npy')  # (n_sea, n_base)
base_dates_str = np.load('/tmp/base_dates.npy')
base_dates = [datetime.strptime(s, '%Y%m%d') for s in base_dates_str]
date_to_idx = {d.strftime('%Y%m%d'): i for i, d in enumerate(base_dates)}

with open('/tmp/doy_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)

n_sea = base_sst_sea.shape[0]
print(f"n_sea: {n_sea}, n_base: {base_sst_sea.shape[1]}")

# For each DOY, compute threshold and climatology for each sea cell
# Initialize arrays
threshold_raw = np.full((366, n_sea), np.nan, dtype=np.float64)  # threshold[day_of_year-1, sea_cell]
clim_raw = np.full((366, n_sea), np.nan, dtype=np.float64)  # climatology[day_of_year-1, sea_cell]

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = doy_to_pool_dates[doy]
    pool_indices = [date_to_idx[d.strftime('%Y%m%d')] for d in pool_dates]
    pool_data = base_sst_sea[:, pool_indices]  # (n_sea, n_pool_dates)
    
    # Compute 90th percentile and mean, ignoring NaN
    # For each sea cell, compute across the pool dimension
    # Use numpy nanpercentile with method='hazen' and nanmean
    for c in range(n_sea):
        vals = pool_data[c]
        valid = ~np.isnan(vals)
        if valid.sum() > 0:
            threshold_raw[doy-1, c] = np.percentile(vals[valid], 90, method='hazen')
            clim_raw[doy-1, c] = np.mean(vals[valid])
        # else: leave as NaN (no valid data)

print("Computed raw thresholds and climatologies")
print(f"NaN thresholds: {np.isnan(threshold_raw).sum()}")
print(f"NaN climatologies: {np.isnan(clim_raw).sum()}")

# Set DOY 60 as mean of DOY 59 and 61
threshold_raw[59, :] = (threshold_raw[58, :] + threshold_raw[60, :]) / 2
clim_raw[59, :] = (clim_raw[58, :] + clim_raw[60, :]) / 2

print("Set DOY 60")
print(f"After setting DOY 60, NaN thresholds: {np.isnan(threshold_raw).sum()}")
print(f"After setting DOY 60, NaN climatologies: {np.isnan(clim_raw).sum()}")

np.save('/tmp/threshold_raw.npy', threshold_raw)
np.save('/tmp/clim_raw.npy', clim_raw)
print("Saved raw threshold and climatology")
