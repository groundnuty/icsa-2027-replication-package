
import numpy as np

# Recompute and then smooth
# Actually, I need the threshold_raw and clim_raw from the previous computation
# They were computed but the process ended. Let me redo it.

import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

base_data = np.load('/tmp/base_data.npy')
base_times = np.load('/tmp/base_times.npy')

def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

def date_to_doy(dt):
    return day_of_year(dt.month, dt.day)

base_dt = [pd.Timestamp(t).to_pydatetime() for t in base_times]

baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

doy_to_baseline_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d)
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

date_to_idx = {}
for i, dt in enumerate(base_dt):
    date_to_idx[dt] = i

doy_to_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    indices = set()
    for Y in doy_to_baseline_dates.get(d, []):
        for i in range(-5, 6):
            X = Y + timedelta(days=i)
            if X in date_to_idx:
                indices.add(date_to_idx[X])
    doy_to_pool_indices[d] = sorted(indices)

threshold_raw = np.zeros((366, 60, 60))
clim_raw = np.zeros((366, 60, 60))

for d in range(1, 367):
    if d == 60:
        continue
    indices = doy_to_pool_indices[d]
    pool_data = base_data[indices]
    threshold_raw[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method="hazen")
    clim_raw[d-1] = np.nanmean(pool_data, axis=0)

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2.0
clim_raw[59] = (clim_raw[58] + clim_raw[60]) / 2.0

# Smooth with 31-day moving average wrapping around
def smooth_wrap(arr):
    """arr: (366, ...) array, smooth along first axis with 31-day window wrapping."""
    # For each day i, average days i-15 to i+15 modulo 366
    # Use rolling approach: create extended array of 366 + 30 elements
    n = arr.shape[0]  # should be 366
    result = np.zeros_like(arr)
    for i in range(n):
        indices = [(i + j) % n for j in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold_raw)
clim_smooth = smooth_wrap(clim_raw)

print("Smoothed threshold shape:", threshold_smooth.shape)
print("Smoothed clim shape:", clim_smooth.shape)

# Check some values
print(f"DOY 1 smoothed threshold[0,0]: {threshold_smooth[0,0,0]:.4f}")
print(f"DOY 60 smoothed threshold[0,0]: {threshold_smooth[59,0,0]:.4f}")
print(f"DOY 153 smoothed threshold[0,0]: {threshold_smooth[152,0,0]:.4f}")
print(f"DOY 244 smoothed threshold[0,0]: {threshold_smooth[243,0,0]:.4f}")
print(f"DOY 366 smoothed threshold[0,0]: {threshold_smooth[365,0,0]:.4f}")

print(f"DOY 1 smoothed clim[0,0]: {clim_smooth[0,0,0]:.4f}")
print(f"DOY 153 smoothed clim[0,0]: {clim_smooth[152,0,0]:.4f}")

# Check for NaN
print("NaN in smoothed threshold:", np.isnan(threshold_smooth).sum())
print("NaN in smoothed clim:", np.isnan(clim_smooth).sum())

# Save results
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/clim_smooth.npy', clim_smooth)
print("Saved smoothed threshold and climatology.")
