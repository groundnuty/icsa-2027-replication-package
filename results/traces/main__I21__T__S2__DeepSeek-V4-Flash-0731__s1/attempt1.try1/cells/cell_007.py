
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import pandas as pd

# Load data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values
baseline_time = baseline_data.time.values
target_sst = target_data.analysed_sst.values
target_time = target_data.time.values

baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]

# Define day_of_year function
def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

# For each day-of-year d (1-366), find the indices in baseline data that belong to its pool
# A baseline index i belongs to day-of-year d's pool if its date is within ±5 days of
# some baseline date (1992-2002) with day-of-year d.

# First, identify which baseline indices correspond to dates within 1992-2002
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)

# For each day-of-year d, find all baseline dates in 1992-2002 with that day of year
# Then for each such date, find all indices within ±5 days

doy_to_indices = {}  # day-of-year -> list of baseline indices in the pool

# For each day-of-year d from 1 to 366 (excluding 60)
for d in range(1, 367):
    if d == 60:
        continue
    # Find all dates in 1992-2002 baseline period with day_of_year = d
    pool_indices = set()
    for i, dt in enumerate(baseline_dates):
        if base_start <= dt <= base_end and day_of_year(dt) == d:
            # This is a baseline date with day_of_year d
            # All indices within ±5 days belong to the pool
            for j in range(max(0, i-5), min(len(baseline_dates), i+6)):
                pool_indices.add(j)
    doy_to_indices[d] = sorted(pool_indices)

# Verify some basic properties
print(f"Number of day-of-year values with pools: {len(doy_to_indices)}")
print(f"Pool size for day 1: {len(doy_to_indices[1])}")
print(f"Pool size for day 100: {len(doy_to_indices[100])}")
print(f"Pool size for day 366: {len(doy_to_indices[366])}")
print(f"Pool size for day 59: {len(doy_to_indices[59])}")
print(f"Pool size for day 61: {len(doy_to_indices[61])}")
