
import numpy as np
import datetime
from collections import defaultdict

baseline_sst = np.load('/tmp/baseline_sst.npy')
baseline_times = np.load('/tmp/baseline_times.npy')
baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

baseline_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    baseline_date_to_idx[d] = i

# Build doy pools
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

# Verify threshold for a specific cell and day
target_sst = np.load('/tmp/target_sst.npy')
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

sea_cells = np.argwhere(sea_mask)
si, sj = sea_cells[0]

# For day 153 (index 152)
doy = 153
idx = doy_pool_indices[doy]
pool_vals = baseline_sst[idx, si, sj]
pool_vals = pool_vals[np.isfinite(pool_vals)]
print(f"Cell ({si},{sj}), doy 153:")
print(f"  Pool size: {len(pool_vals)}")
print(f"  Pool values (first 10): {pool_vals[:10]}")
print(f"  Pool values (last 10): {pool_vals[-10:]}")
print(f"  Mean: {np.mean(pool_vals)}")
print(f"  Hazen 90th percentile: {np.percentile(pool_vals, 90, method='hazen')}")

# Compare with stored raw threshold
threshold_raw = np.load('/tmp/threshold_raw.npy')
print(f"  Stored raw threshold: {threshold_raw[152, si, sj]}")
print(f"  Stored raw climatology: {np.load('/tmp/climatology_raw.npy')[152, si, sj]}")
