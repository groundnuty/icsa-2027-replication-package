
import numpy as np
import datetime
from collections import defaultdict

baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')
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

n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Check if any sea cell has all-NaN in a specific day-of-year pool
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

# Check if any sea cell has all-NaN pool for any doy
problem_cells = []
for doy in range(1, 367):
    if doy == 60:
        continue
    idx = doy_pool_indices[doy]
    pool = baseline_sst[idx, :, :]
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i,j]:
                if not np.any(np.isfinite(pool[:, i, j])):
                    problem_cells.append((doy, i, j))

print(f"Problem cells (sea cell with all-NaN pool): {len(problem_cells)}")
if problem_cells:
    print(problem_cells[:10])
