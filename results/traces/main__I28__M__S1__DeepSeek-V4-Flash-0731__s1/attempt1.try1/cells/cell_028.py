
import numpy as np
from datetime import date, timedelta

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load threshold and check smoothing manually
threshold = np.load('/tmp/threshold.npy')
climatology = np.load('/tmp/climatology.npy')

# Verify smoothing for doy 153, cell (0,0)
# Manually compute the 31-day centered moving mean
# Day 153 (index 152 in 0-indexed): average days 138-168 (indices 137-167, mod 366)
target_idx = 152  # 0-indexed for doy 153
idxs = [(target_idx + k) % 366 for k in range(-15, 16)]
print(f"Indices for smoothing doy 153: {idxs}")
print(f"Number of indices: {len(idxs)}")
print(f"Threshold values at these indices for cell (0,0):")
print(threshold[idxs, 0, 0])
manual_mean = np.mean(threshold[idxs, 0, 0])
print(f"Manual mean: {manual_mean}")

# Now load the smoothed threshold
# Actually, we didn't save it. Let me recompute the smoothing.
def smooth_31(a):
    n = 366
    result = np.full_like(a, np.nan)
    for i in range(n):
        idxs = [(i + k) % n for k in range(-15, 16)]
        result[i] = np.nanmean(a[idxs], axis=0)
    return result

threshold_smooth = smooth_31(threshold)
print(f"Smoothed threshold at doy 153, cell (0,0): {threshold_smooth[152, 0, 0]}")
print(f"Match: {abs(threshold_smooth[152, 0, 0] - manual_mean) < 1e-10}")

# Verify day 60 handling
print(f"\nDay 59 threshold (cell 0,0): {threshold[58, 0, 0]}")
print(f"Day 60 threshold (cell 0,0): {threshold[59, 0, 0]}")
print(f"Day 61 threshold (cell 0,0): {threshold[60, 0, 0]}")
print(f"Day 60 = (day 59 + day 61)/2: {(threshold[58, 0, 0] + threshold[60, 0, 0])/2}")

# Verify pool sizes
# Load baseline date info
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {d: i for i, d in enumerate(all_dates)}
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

# Check pool for doy 153
doy = 153
pool = []
for D in baseline_1992_2002:
    if doy_of_date(D) == doy:
        for k in range(-5, 6):
            X = D + timedelta(days=k)
            if X in date_to_idx:
                pool.append(date_to_idx[X])
print(f"\nPool size for doy 153: {len(pool)}")
print(f"Pool dates for doy 153 (first 11): {[all_dates[i].strftime('%Y-%m-%d') for i in pool[:11]]}")
