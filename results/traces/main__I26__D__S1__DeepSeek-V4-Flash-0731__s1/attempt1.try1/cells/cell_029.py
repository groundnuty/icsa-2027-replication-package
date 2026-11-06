import numpy as np
from datetime import datetime, timedelta
import json

# Load saved data
baseline_data = np.load('/work/baseline_data.npy')  # (4028, 60, 60) float32
target_data = np.load('/work/target_data.npy')      # (92, 60, 60) float32

# Convert to float64
baseline_data = baseline_data.astype(np.float64)
target_data = target_data.astype(np.float64)

print("Baseline shape:", baseline_data.shape, baseline_data.dtype)
print("Target shape:", target_data.shape, target_data.dtype)

# Day-of-year mapping function
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Generate all extraction dates
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
print(f"Extraction dates: {len(all_dates)}")

# Baseline dates (1992-01-01 to 2002-12-31)
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)
baseline_dates = [dt for dt in all_dates if base_start <= dt <= base_end]
baseline_doy = [day_of_year(dt.month, dt.day) for dt in baseline_dates]

# Build pools: for each day-of-year d (1-366, d≠60), collect indices of dates 
# within ±5 days of any baseline date with day-of-year d
from collections import defaultdict

# Map from baseline date index (in all_dates) to its doy
base_idx_in_all = []
for dt in baseline_dates:
    base_idx_in_all.append(all_dates.index(dt))

# Build doy -> list of indices in all_dates
doy_pool_indices = defaultdict(list)
for k, doy in enumerate(baseline_doy):
    if doy == 60:
        continue
    bidx = base_idx_in_all[k]
    for i in range(max(0, bidx - 5), min(len(all_dates), bidx + 6)):
        doy_pool_indices[doy].append(i)

# Convert to sorted unique lists
for doy in doy_pool_indices:
    doy_pool_indices[doy] = sorted(set(doy_pool_indices[doy]))

print(f"Built pools for {len(doy_pool_indices)} day-of-year values")
print(f"Pool sizes: min={min(len(v) for v in doy_pool_indices.values())}, max={max(len(v) for v in doy_pool_indices.values())}")
