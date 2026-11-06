
import numpy as np
import datetime

# Manual verification of one threshold value
baseline_sst = np.load('baseline_sst.npy')
base_dates = np.load('base_dates.npy')
base_dates = [datetime.date.fromordinal(int(x)) for x in base_dates]
threshold_smooth = np.load('threshold_smooth.npy')

def date_to_doy(d):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

date_to_idx = {d: i for i, d in enumerate(base_dates)}
baseline_dates = [d for d in base_dates if 1992 <= d.year <= 2002]

# Pick doy=180 and cell (3, 35)
doy = 180
i, j = 3, 35

# Build pool for doy=180
pool_idx = []
for bd in baseline_dates:
    if date_to_doy(bd) == doy:
        for offset in range(-5, 6):
            idx = date_to_idx.get(bd + datetime.timedelta(days=offset))
            if idx is not None:
                pool_idx.append(idx)

pool_values = baseline_sst[pool_idx, i, j]
pool_values = pool_values[np.isfinite(pool_values)]
print(f"Pool for doy={doy}, cell=({i},{j}): {len(pool_values)} values")

# Compute unsmoothed threshold (Hazen 90th percentile)
unsmoothed_thr = np.quantile(pool_values, 0.9, method='hazen')
print(f"Unsmoothed threshold: {unsmoothed_thr}")

# Check what the smoothed threshold should be
# The smoothed threshold at doy=180 averages unsmoothed thresholds for doys 165-195
# We need to reconstruct the unsmoothed threshold for all doys

# Actually, let me just verify the raw threshold for this cell and doy
# by checking against the pre-smoothing threshold array
# We don't have the unsmoothed threshold saved, so let me just check
# that the smoothed value is reasonable

print(f"Smoothed threshold at doy=180: {threshold_smooth[doy-1, i, j]}")
print(f"Pool mean (climatology): {np.mean(pool_values)}")

# Verify that the unsmoothed threshold should be close to the smoothed one
# for mid-summer when values are stable
print(f"\nSmoothed threshold at doys 170-190 for cell ({i},{j}):")
for d in range(170, 191):
    print(f"  doy={d}: {threshold_smooth[d-1, i, j]:.4f}")
