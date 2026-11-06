
import numpy as np

# Verify np.percentile with hazen method
# Create a test dataset
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90 = np.percentile(data, 90, method='hazen')
print(f"90th percentile (hazen) of 1..10: {p90}")

# MATLAB's quantile with default settings should give:
# h = (n-1)*p + 1 = 9*0.9 + 1 = 9.1
# Q = x[8] + 0.1*(x[9]-x[8]) = 9 + 0.1 = 9.1
# But numpy's hazen gives 9.5

# Let me verify this is what numpy actually computes
# hazen: virtual_index = n*p - 0.5 = 10*0.9 - 0.5 = 8.5
# previous = x[8] = 9, next = x[9] = 10
# gamma = 8.5 - 8 = 0.5
# result = 9 + 0.5*(10-9) = 9.5

# Let me verify the task's claim that this matches MATLAB's quantile
# Actually, the task says "computed as MATLAB's quantile does by default, 
# which is numpy's method='hazen' (Hyndman-Fan type 5), ignoring NaN"
# So I should just use numpy's method='hazen'

# Let me verify my pool construction and percentile computation for one cell
import pandas as pd
from datetime import datetime, timedelta

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
baseline_time = np.load('/tmp/baseline_time.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
base_doy = np.array([doy_from_date(d) for d in baseline_dates])

strict_base_start = pd.Timestamp('1992-01-01')
strict_base_end = pd.Timestamp('2002-12-31')
strict_idx = np.where([(d >= strict_base_start and d <= strict_base_end) for d in baseline_dates])[0]

base_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Check DOY 153 (June 1) for a specific sea cell
d = 153
dates_with_doy = []
for i in strict_idx:
    if base_doy[i] == d:
        dates_with_doy.append(baseline_dates[i])

pool_indices = set()
for bd in dates_with_doy:
    for offset in range(-5, 6):
        candidate = bd + timedelta(days=offset)
        if candidate in base_date_to_idx:
            pool_indices.add(base_date_to_idx[candidate])

pool_indices = sorted(pool_indices)

# Get values for first sea cell
sea_indices = np.where(sea_mask)
lat_i, lon_j = sea_indices[0][0], sea_indices[1][0]

baseline_sst64 = baseline_sst.astype(np.float64)
values = baseline_sst64[pool_indices, lat_i, lon_j]
valid = values[~np.isnan(values)]
print(f"\nDOY 153 pool for first sea cell:")
print(f"  Total pool size: {len(values)}")
print(f"  Valid values: {len(valid)}")
print(f"  NaN values: {len(values) - len(valid)}")
print(f"  Min/Max: {np.min(valid):.2f} / {np.max(valid):.2f}")
print(f"  Mean: {np.mean(valid):.2f}")
print(f"  90th percentile (hazen): {np.percentile(valid, 90, method='hazen'):.2f}")
