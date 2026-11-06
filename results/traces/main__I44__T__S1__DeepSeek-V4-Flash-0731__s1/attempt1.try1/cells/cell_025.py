import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd
from collections import defaultdict

# Load data
base_ds = xr.open_dataset('/tmp/base_data.nc')
base_sst = base_ds['analysed_sst'].values.astype(np.float64)
base_time = base_ds['time'].values

base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)

# Let me verify pool for DOY 1
# Baseline dates with DOY 1: Jan 1 of each year 1992-2002
# Window: Dec 27 to Jan 6 around each Jan 1

doy1_baseline = []
for date in base_dates:
    if baseline_start <= date <= baseline_end and day_of_year(date) == 1:
        doy1_baseline.append(date)
print("DOY 1 baseline dates:", doy1_baseline[:3], "...", doy1_baseline[-3:], "count:", len(doy1_baseline))

# For each baseline date, the window is ±5 days
# Check: for 1992-01-01, window is 1991-12-27 to 1992-01-06
# The task says "windows near the ends of the baseline reach up to 5 days beyond it (1991-12-27 to 1991-12-31)"
# 1991-12-27 is in our extended baseline range (we loaded 1991-12-27 onwards)

# Let me verify DOY 1 pool dates
doy1_pool_dates = []
for b in doy1_baseline:
    for delta in range(-5, 6):
        t = b + dt.timedelta(days=delta)
        if baseline_start - dt.timedelta(days=6) <= t <= baseline_end + dt.timedelta(days=6):
            # Check if t is in our loaded data
            doy1_pool_dates.append(t)

doy1_pool_dates = sorted(set(doy1_pool_dates))
print("DOY 1 pool dates:", len(doy1_pool_dates))
print("First few:", doy1_pool_dates[:5])
print("Last few:", doy1_pool_dates[-5:])

# For 1992: window = 1991-12-27 to 1992-01-06
# Our data starts at 1991-12-27, so all should be included
# For 2002: window = 2001-12-27 to 2002-01-06
# For 2003: no baseline date with DOY 1 in 2003 (that's outside baseline)

# Check: what about the last year? 2002-01-01 has DOY 1.
# Window: 2001-12-27 to 2002-01-06

# Verify some specific dates are in the pool
print("1991-12-27 in pool:", dt.date(1991,12,27) in doy1_pool_dates)
print("2002-01-06 in pool:", dt.date(2002,1,6) in doy1_pool_dates)

# Now verify DOY 366 pool
# Baseline dates with DOY 366: Dec 31 of each year 1992-2002
doy366_baseline = []
for date in base_dates:
    if baseline_start <= date <= baseline_end and day_of_year(date) == 366:
        doy366_baseline.append(date)
print("\nDOY 366 baseline dates:", doy366_baseline[:3], "...", doy366_baseline[-3:])

# For 2002-12-31: window = 2002-12-26 to 2003-01-05
# 2003-01-01 to 2003-01-05 should be in the pool
doy366_pool_dates = []
for b in doy366_baseline:
    for delta in range(-5, 6):
        t = b + dt.timedelta(days=delta)
        doy366_pool_dates.append(t)
doy366_pool_dates = sorted(set(doy366_pool_dates))
print("DOY 366 pool dates count:", len(doy366_pool_dates))
print("2003-01-01 in pool:", dt.date(2003,1,1) in doy366_pool_dates)
print("2003-01-05 in pool:", dt.date(2003,1,5) in doy366_pool_dates)
print("2003-01-06 in pool:", dt.date(2003,1,6) in doy366_pool_dates)

# Now let me check the day 60 handling more carefully
# Day 60 = Feb 29 in leap years (1992, 1996, 2000 in baseline)
# "29 February values belong to the windows of their calendar neighbours"
# This means Feb 29 values should be in the pools for day 59 (Feb 28) and day 61 (Mar 1)

# For day 59 (Feb 28), the window includes dates from Feb 23 to Mar 5
# For each baseline year, Feb 29 is within ±5 days of Feb 28
# So Feb 29 values are automatically included in the day 59 pool

# Let me verify: does the pool for DOY 59 include Feb 29 dates?
doy59_baseline = []
for date in base_dates:
    if baseline_start <= date <= baseline_end and day_of_year(date) == 59:
        doy59_baseline.append(date)
print("\nDOY 59 baseline dates:", doy59_baseline[:3])

# Check if Feb 29 1992 is within ±5 days of Feb 28 1992 (which has DOY 59)
feb29_1992 = dt.date(1992, 2, 29)
feb28_1992 = dt.date(1992, 2, 28)
print("Feb 29 1992 within 5 days of Feb 28 1992:", abs((feb29_1992 - feb28_1992).days) <= 5)

# Yes, so Feb 29 values are automatically in the pool for DOY 59 via the ±5 day window.
# Similarly for DOY 61 (Mar 1).

# So the statement "29 February values belong to the windows of their calendar neighbours"
# is a natural consequence of the ±5 day window approach, since Feb 29 is within ±5 days 
# of both Feb 28 and Mar 1.

# Day 60 (Feb 29) itself gets no pool of its own, and its threshold/climatology
# is set to the mean of days 59 and 61.
