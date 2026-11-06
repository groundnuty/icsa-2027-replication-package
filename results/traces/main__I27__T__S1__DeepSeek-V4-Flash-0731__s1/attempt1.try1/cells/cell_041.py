
import numpy as np
import pandas as pd
import datetime

# Define day-of-year mapping (fixed 366-day calendar)
def date_to_doy(dt):
    """Convert a date to day of year 1-366."""
    days_in_month_fixed = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month_fixed[:dt.month]) + dt.day

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
target_data = np.load('/tmp/target_data.npy')
baseline_times = pd.DatetimeIndex(np.load('/tmp/baseline_times.npy').astype('datetime64[ns]'))
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))

# Verify day-of-year mapping
test_dates = [
    ('1992-01-01', 1),
    ('1992-02-28', 59),
    ('1992-02-29', 60),
    ('1992-03-01', 61),
    ('1992-12-31', 366),
    ('1993-01-01', 1),
    ('1993-02-28', 59),
    ('1993-03-01', 61),
    ('1993-12-31', 366),
]
for date_str, expected in test_dates:
    dt = pd.Timestamp(date_str)
    doy = date_to_doy(dt)
    print(f"{date_str}: doy={doy}, expected={expected}, {'OK' if doy == expected else 'MISMATCH'}")

# Build the pool date indices for each day of year
# The baseline period for pool construction is 1992-01-01 to 2002-12-31
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

# All dates in the full loaded baseline data
all_baseline_dates = [pd.Timestamp(t) for t in baseline_times]

# For each day of year d (1-366 except 60), find all dates in all_baseline_dates 
# that are within ±5 calendar days of a baseline date (in 1992-2002) with doy = d
# 
# Strategy: 
# 1. Find baseline dates (1992-01-01 to 2002-12-31) with doy = d
# 2. For each such date, the window is [date - 5 days, date + 5 days]
# 3. Collect all dates in all_baseline_dates that fall in any of these windows

# First, let's identify baseline dates by their doy
baseline_dates_1992_2002 = [d for d in all_baseline_dates if baseline_start <= d <= baseline_end]
print(f"\nBaseline dates in 1992-2002: {len(baseline_dates_1992_2002)}")

# Group baseline dates by doy
baseline_dates_by_doy = {}
for d in baseline_dates_1992_2002:
    doy = date_to_doy(d)
    if doy not in baseline_dates_by_doy:
        baseline_dates_by_doy[doy] = []
    baseline_dates_by_doy[doy].append(d)

# Check which days of year are present
missing_doy = set(range(1, 367)) - set(baseline_dates_by_doy.keys())
print(f"Missing DOYs (should be just 60 for non-leap years... but wait, we need to check): {sorted(missing_doy)}")

# Day 60 only occurs in leap years within 1992-2002: 1992, 1996, 2000
print(f"Day 60 baseline dates: {baseline_dates_by_doy.get(60, [])}")
