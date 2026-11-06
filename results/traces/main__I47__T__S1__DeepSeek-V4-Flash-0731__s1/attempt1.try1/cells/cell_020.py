
import numpy as np

# Load the computed threshold and climatology
# I need to recompute them since they're in memory from the previous step
# Actually they should still be in the same process, but let me check

# Let me reload and recompute
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

print("After setting day 60:")
print(f"DOY 59 threshold[0,0]={threshold_raw[58,0,0]:.4f}")
print(f"DOY 60 threshold[0,0]={threshold_raw[59,0,0]:.4f}")
print(f"DOY 61 threshold[0,0]={threshold_raw[60,0,0]:.4f}")
print(f"DOY 59 clim[0,0]={clim_raw[58,0,0]:.4f}")
print(f"DOY 60 clim[0,0]={clim_raw[59,0,0]:.4f}")
print(f"DOY 61 clim[0,0]={clim_raw[60,0,0]:.4f}")

# Check for NaN
print("NaN in threshold after day 60:", np.isnan(threshold_raw).sum())
print("NaN in clim after day 60:", np.isnan(clim_raw).sum())

# Which cells have NaN?
nan_cells_threshold = np.isnan(threshold_raw).any(axis=0)
print("Cells with any NaN threshold:", nan_cells_threshold.sum())
nan_cells_clim = np.isnan(clim_raw).any(axis=0)
print("Cells with any NaN clim:", nan_cells_clim.sum())
