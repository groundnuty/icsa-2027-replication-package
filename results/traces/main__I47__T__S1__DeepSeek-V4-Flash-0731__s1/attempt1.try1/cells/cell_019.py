
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

# Load saved data
base_data = np.load('/tmp/base_data.npy')
tgt_data = np.load('/tmp/tgt_data.npy')
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')

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

# Build pool indices for each doy
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

# Compute threshold and climatology for each doy
# threshold_raw[0:366] for doy 1-366 (using 0-based index: doy-1)
# shape: (366, 60, 60)

N_CELLS = 60 * 60
threshold_raw = np.zeros((366, 60, 60))
clim_raw = np.zeros((366, 60, 60))

for d in range(1, 367):
    if d == 60:
        continue
    indices = doy_to_pool_indices[d]
    pool_data = base_data[indices]  # (N, 60, 60)
    # Compute per-cell 90th percentile (hazen) and mean, ignoring NaN
    # np.nanquantile and np.nanmean operate on the first axis (axis=0)
    threshold_raw[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method="hazen")
    clim_raw[d-1] = np.nanmean(pool_data, axis=0)
    
    if d in [1, 60, 61, 153, 244, 366]:
        print(f"DOY {d}: threshold[0,0]={threshold_raw[d-1,0,0]:.4f}, clim[0,0]={clim_raw[d-1,0,0]:.4f}")

print("Computed threshold and climatology for all DOYs")
print("Any NaN in threshold:", np.isnan(threshold_raw).any())
print("Any NaN in climatology:", np.isnan(clim_raw).any())
