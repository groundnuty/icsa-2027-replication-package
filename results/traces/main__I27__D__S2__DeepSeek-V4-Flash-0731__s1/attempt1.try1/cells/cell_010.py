
import numpy as np

baseline_arr = np.load('/work/baseline_arr.npy')

# Recompute doy_to_pool_indices
import pandas as pd

def date_to_doy(dt):
    d = pd.Timestamp(dt)
    month, day = d.month, d.day
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

baseline_time = np.load('/work/baseline_time.npy').astype('datetime64[D]')
date_to_idx = {t: i for i, t in enumerate(baseline_time)}

baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

doy_to_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    dates_with_doy = [bd for bd in baseline_dates if date_to_doy(bd) == d]
    pool_dates = set()
    for bd in dates_with_doy:
        for offset in range(-5, 6):
            pool_dates.add(np.datetime64(bd) + np.timedelta64(offset, 'D'))
    idx = [date_to_idx[t] for t in sorted(pool_dates)]
    doy_to_pool_indices[d] = np.array(idx)

# Now compute thresholds and climatology for each doy and each sea cell
nlat, nlon = baseline_arr.shape[1], baseline_arr.shape[2]

# For each doy, extract pool values for all cells
# This might be memory-intensive, let's do it one doy at a time
thresholds = np.full((366, nlat, nlon), np.nan)
climatology = np.full((366, nlat, nlon), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    idx = doy_to_pool_indices[d]
    pool = baseline_arr[idx, :, :]  # (npool, nlat, nlon)
    
    # Compute threshold (90th percentile, Hazen method, ignoring NaN)
    # For each cell
    for i in range(nlat):
        for j in range(nlon):
            vals = pool[:, i, j]
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                thresholds[d, i, j] = np.percentile(valid, 90, method='hazen')
                climatology[d, i, j] = np.mean(valid)
            # else: remains NaN (no valid data)

print("Computed thresholds and climatology for days 1-366 except 60")

# Set day 60 to mean of days 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Check some values
print("Threshold day 59 cell (0,0):", thresholds[59, 0, 0])
print("Threshold day 60 cell (0,0):", thresholds[59, 0, 0])  # day 60 is index 59 (0-based)
print("Threshold day 61 cell (0,0):", thresholds[60, 0, 0])

# Save
np.save('/work/thresholds.npy', thresholds)
np.save('/work/climatology.npy', climatology)
print("Saved")
