
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict

# Verify smoothing manually for a specific case
baseline_data = xr.open_dataset('baseline_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')

# Let me verify that the smoothing function was correct by reconstructing it
# For a specific cell and day of year

# Check: the smoothed threshold for day 100 at cell (0,0)
# Should be the average of raw thresholds for days 85-115 (mod 366)

# But I didn't save the raw (unsmoothed) thresholds. Let me recompute them.
# Actually, let me just check the smoothing logic by re-running the full pipeline

# Rebuild the pools and compute raw thresholds for cell (0,0)
baseline_sst = baseline_data.analysed_sst.values

cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

all_dates_np = baseline_data.time.values.astype('datetime64[D]')
all_date_objs = [pd.Timestamp(t).date() for t in all_dates_np]

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

baseline_date_objs = [d for d in all_date_objs if baseline_start <= d <= baseline_end]

doy_to_baseline_dates = defaultdict(list)
for d in baseline_date_objs:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)

date_to_idx = {d: i for i, d in enumerate(all_date_objs)}

doy_to_date_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = set()
    for b in doy_to_baseline_dates.get(doy, []):
        for delta in range(-5, 6):
            t = b + timedelta(days=delta)
            if t in date_to_idx:
                pool_indices.add(date_to_idx[t])
    doy_to_date_indices[doy] = sorted(pool_indices)

# Compute raw thresholds for cell (0,0)
raw_thresholds = np.zeros(367)  # index 0 unused, 1-366 for days of year
for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = doy_to_date_indices[doy]
    vals = baseline_sst[idxs, 0, 0].astype(np.float64)
    vals_clean = vals[~np.isnan(vals)]
    if len(vals_clean) > 0:
        raw_thresholds[doy] = np.percentile(vals_clean, 90, method='hazen')
    else:
        raw_thresholds[doy] = np.nan

# Set day 60
raw_thresholds[60] = (raw_thresholds[59] + raw_thresholds[61]) / 2.0

# Manual smoothing for day 100
# Day 100 averages days 85-115 (mod 366)
vals = []
for k in range(100-15, 100+16):
    idx = ((k-1) % 366) + 1  # Convert to 1-based day of year
    vals.append(raw_thresholds[idx])

manual_smooth_100 = np.mean([v for v in vals if not np.isnan(v)])
print(f"Manual smoothed threshold for day 100, cell (0,0): {manual_smooth_100}")
print(f"From stored array: {thresholds_smooth[100, 0, 0]}")

# Check a wrap-around case: day 5
# Days 351-366 and 1-20 (mod 366), i.e., days 352-366 and 1-20
# Wait, day 5 averages days -10 to 20, mod 366. -10 mod 366 = 356, -1 mod 366 = 365.
# So days 356-366 and 1-20.
vals = []
for k in range(5-15, 5+16):
    idx = ((k-1) % 366) + 1
    vals.append(raw_thresholds[idx])
manual_smooth_5 = np.mean([v for v in vals if not np.isnan(v)])
print(f"Manual smoothed threshold for day 5, cell (0,0): {manual_smooth_5}")
print(f"From stored array: {thresholds_smooth[5, 0, 0]}")

# Check day 366
# Day 366 averages days 351-366 and 1-15 (mod 366)
vals = []
for k in range(366-15, 366+16):
    idx = ((k-1) % 366) + 1
    vals.append(raw_thresholds[idx])
manual_smooth_366 = np.mean([v for v in vals if not np.isnan(v)])
print(f"Manual smoothed threshold for day 366, cell (0,0): {manual_smooth_366}")
print(f"From stored array: {thresholds_smooth[366, 0, 0]}")
