import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd

# Load data
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')
base_sst = base_ds['analysed_sst'].values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
base_time = base_ds['time'].values
target_time = target_ds['time'].values

# Convert to dates
base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

# Verify baseline dates within 1992-2002
baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)

# Build a mapping: for each day-of-year d (1-366), find the baseline dates with that DOY
# And for each such baseline date, find all dates within ±5 calendar days
# that are in the extended baseline range

# For efficiency, I'll pre-compute for each day-of-year d which time indices in base_dates
# belong to the pool for d.

# First, let me find the baseline dates for each DOY
# baseline_dates_by_doy[d] = list of dates in 1992-2002 with DOY = d
from collections import defaultdict
baseline_dates_by_doy = defaultdict(list)
for date in base_dates:
    if baseline_start <= date <= baseline_end:
        d = day_of_year(date)
        baseline_dates_by_doy[d].append(date)

# Check
print("DOY 1 dates:", baseline_dates_by_doy[1][:3], "...", baseline_dates_by_doy[1][-3:])
print("DOY 59 dates:", baseline_dates_by_doy[59][:3])
print("DOY 60 dates:", baseline_dates_by_doy[60][:3])
print("DOY 61 dates:", baseline_dates_by_doy[61][:3])
print("DOY 366 dates:", baseline_dates_by_doy[366][:3])
print("Number of DOYs with baseline dates:", len(baseline_dates_by_doy))

# All DOYs 1-366 except 60 should have baseline dates
missing = set(range(1,367)) - set(baseline_dates_by_doy.keys()) - {60}
print("Missing DOYs:", missing)
