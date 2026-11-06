
import numpy as np
import pandas as pd

# Load data
baseline_arr = np.load('/work/baseline_arr.npy')
thr_smooth = np.load('/work/thr_smooth.npy')
cli_smooth = np.load('/work/cli_smooth.npy')

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

# Pick a day of year (e.g., 153, which is June 1 in leap year convention)
# June: cum[5] = 152, so June 1 = 153
doy = 153

# Find baseline dates with doy = 153
dates_with_doy = [bd for bd in baseline_dates if date_to_doy(bd) == doy]
print("Baseline dates with doy", doy, ":", dates_with_doy)

# Build pool dates
pool_dates = set()
for bd in dates_with_doy:
    for offset in range(-5, 6):
        pool_dates.add(np.datetime64(bd) + np.timedelta64(offset, 'D'))
pool_dates = sorted(pool_dates)
print("Pool dates:", pool_dates)

# Get pool indices
pool_idx = [date_to_idx[t] for t in pool_dates]
print("Pool indices:", pool_idx)

# Check a sea cell
# Cell (0,0) is a sea cell (from earlier verification)
i, j = 0, 0
pool_vals = baseline_arr[pool_idx, i, j]
valid = pool_vals[~np.isnan(pool_vals)]
print("\nPool size:", len(pool_vals), "Valid:", len(valid))
print("Valid values:", valid)

# Manual threshold and climatology
manual_thr = np.percentile(valid, 90, method='hazen')
manual_cli = np.mean(valid)
print("Manual threshold:", manual_thr)
print("Manual climatology:", manual_cli)

# Check unsmoothed threshold
# We saved thresholds before smoothing
# Let me recompute for this specific case
# thresholds[doy-1, i, j] should be the unsmoothed value
# But I already smoothed... let me just verify the pool values are correct
print("\nPool min:", valid.min(), "max:", valid.max())
print("Pool mean:", valid.mean())
print("Pool sorted:", np.sort(valid))

# The 90th percentile using Hazen method
# For n valid values, position = (n+1)*0.9
n = len(valid)
h = (n + 1) * 0.9
print(f"\nn={n}, h={(n+1)*0.9}")
