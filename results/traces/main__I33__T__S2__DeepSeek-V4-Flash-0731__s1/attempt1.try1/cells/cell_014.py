
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

# Day of year mapping
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

# All dates in the baseline dataset (1991-12-27 to 2003-01-05)
all_dates_np = baseline_data.time.values.astype('datetime64[D]')
all_date_objs = [pd.Timestamp(t).date() for t in all_dates_np]
print("First few:", all_date_objs[:3])
print("Last few:", all_date_objs[-3:])

# For each date, compute its day of year
all_doys = [date_to_doy(d.year, d.month, d.day) for d in all_date_objs]
print("First few DOYs:", all_doys[:5])
print("Last few DOYs:", all_doys[-5:])

# For each day of year d (1-366, excluding 60), find the pool of dates
# Pool for day d = all dates within ±5 calendar days of any baseline date (1992-2002) with day of year d

# First, identify which of the all_dates are "baseline dates" (1992-2002) with day of year d
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# Build a map from day-of-year to list of date indices in all_dates that are within ±5 of a baseline date with that doy
# For each day of year d:
#   Find baseline dates (in 1992-2002) with doy=d
#   For each such baseline date, expand ±5 calendar days
#   Collect all dates from the dataset that fall in any of these windows

# More efficient approach: for each date in all_dates, check which day-of-year pools it belongs to
# A date t belongs to pool d if there exists a baseline date b in 1992-2002 with doy(b)=d and |t-b| <= 5 days

# Let me build this step by step
# First, for each day of year d, find all baseline dates with that doy

from collections import defaultdict

# Baseline dates are in 1992-2002
baseline_date_objs = [d for d in all_date_objs if baseline_start <= d <= baseline_end]
print("Number of baseline dates:", len(baseline_date_objs))

# Group baseline dates by day of year
doy_to_baseline_dates = defaultdict(list)
for d in baseline_date_objs:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)

# For each day of year, verify we have the expected number of baseline dates
for doy in [1, 59, 60, 61, 366]:
    dates_list = doy_to_baseline_dates.get(doy, [])
    print(f"DOY {doy}: {len(dates_list)} baseline dates: {dates_list[:3]} ... {dates_list[-3:]}")
