
import numpy as np
import datetime
from collections import defaultdict

# Load float64 data
baseline_sst = np.load('/tmp/baseline_sst_f64.npy')  # (4028, 60, 60) float64
target_sst = np.load('/tmp/target_sst_f64.npy')       # (92, 60, 60) float64
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

baseline_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    baseline_date_to_idx[d] = i

# Identify sea cells: finite on all target days
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))
print(f"Sea cells: {sea_mask.sum()}")

# Build day-of-year pools
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

doy_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    doy_dates[doy].append(d)
    d += datetime.timedelta(days=1)

doy_pool_indices = {}
for doy, dates in doy_dates.items():
    if doy == 60:
        continue
    pool_dates = set()
    for D in dates:
        for offset in range(-5, 6):
            pool_dates.add(D + datetime.timedelta(days=offset))
    indices = []
    for pd in sorted(pool_dates):
        if pd in baseline_date_to_idx:
            indices.append(baseline_date_to_idx[pd])
    doy_pool_indices[doy] = indices

# Compute thresholds and climatology in float64
n_doy = 366
threshold = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

sea_indices = np.argwhere(sea_mask)
print(f"Processing {len(sea_indices)} sea cells")

for doy in range(1, n_doy + 1):
    if doy == 60:
        continue
    idx = doy_pool_indices[doy]
    pool = baseline_sst[idx, :, :]  # (n_pool, 60, 60) float64
    
    for si, sj in sea_indices:
        vals = pool[:, si, sj]
        vals = vals[np.isfinite(vals)]
        if len(vals) > 0:
            threshold[doy-1, si, sj] = np.percentile(vals, 90, method='hazen')
            climatology[doy-1, si, sj] = np.mean(vals)

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

print("Computed thresholds and climatology in float64")

# Smooth with 31-day centered moving mean, wrapping around
def smooth_wrap(arr):
    result = np.zeros_like(arr)
    n = arr.shape[0]
    for d in range(n):
        indices = [(d + offset) % n for offset in range(-15, 16)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed")

# Save
np.save('/tmp/threshold_smooth_f64.npy', threshold_smooth)
np.save('/tmp/climatology_smooth_f64.npy', climatology_smooth)
np.save('/tmp/sea_mask.npy', sea_mask)

# Quick check
si, sj = sea_indices[0]
print(f"Cell ({si},{sj}), doy 153:")
print(f"  Raw threshold: {threshold[152, si, sj]}")
print(f"  Smooth threshold: {threshold_smooth[152, si, sj]}")
print(f"  Raw clim: {climatology[152, si, sj]}")
print(f"  Smooth clim: {climatology_smooth[152, si, sj]}")
print("Done")
