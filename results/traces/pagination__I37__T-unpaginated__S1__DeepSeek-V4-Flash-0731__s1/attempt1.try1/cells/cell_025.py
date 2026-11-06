
import numpy as np
import datetime
import pickle

# Load data
baseline_sst = np.load('work/baseline_sst.npy')
with open('work/baseline_dates.pkl', 'rb') as f:
    baseline_dates = pickle.load(f)
with open('work/date_to_idx.pkl', 'rb') as f:
    date_to_idx = pickle.load(f)
with open('work/doy_to_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)

doy_to_pool_dates = {k: set(v) for k, v in doy_to_pool_dates.items()}

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Check cell (0,1) for doy 153
cell_i, cell_j = 0, 1
doy = 153

# Get pool dates for doy 153
pool_dates = sorted(doy_to_pool_dates[doy])
print(f"Day {doy} pool has {len(pool_dates)} dates")

# Get pool data for cell (0,1)
pool_idx = [date_to_idx[date] for date in pool_dates]
pool_vals = baseline_sst[pool_idx, cell_i, cell_j]
valid = pool_vals[~np.isnan(pool_vals)]
print(f"Pool values (valid): {len(valid)}")
print(f"Pool values: {valid}")
print(f"Mean: {np.mean(valid):.4f}")
print(f"P90 (hazen): {np.percentile(valid, 90, method='hazen'):.4f}")

# Sort and check
sorted_vals = np.sort(valid)
print(f"Sorted: {sorted_vals}")
n = len(sorted_vals)
print(f"n={n}")
# Check what the Hazen percentile gives
p = np.percentile(sorted_vals, 90, method='hazen')
print(f"90th percentile (hazen): {p:.4f}")

# Also check the percentile using MATLAB's default (linear)
p_linear = np.percentile(sorted_vals, 90, method='linear')
print(f"90th percentile (linear): {p_linear:.4f}")

# For reference, the climatology and threshold we computed
threshold_smooth = np.load('work/threshold_smooth.npy')
climatology_smooth = np.load('work/climatology_smooth.npy')
print(f"\nOur threshold (smoothed) for doy 153, cell (0,1): {threshold_smooth[152, cell_i*60+cell_j]:.4f}")
print(f"Our climatology (smoothed) for doy 153, cell (0,1): {climatology_smooth[152, cell_i*60+cell_j]:.4f}")

# Check unsmoothed values
threshold_raw = np.load('work/threshold.npy')
climatology_raw = np.load('work/climatology.npy')
print(f"Raw threshold for doy 153, cell (0,1): {threshold_raw[152, cell_i*60+cell_j]:.4f}")
print(f"Raw climatology for doy 153, cell (0,1): {climatology_raw[152, cell_i*60+cell_j]:.4f}")
