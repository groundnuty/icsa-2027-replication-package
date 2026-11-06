
import numpy as np
from datetime import datetime, timedelta

def day_of_year(month, day):
    """Map month and day to day of year 1-366 using fixed mapping."""
    month_start = {
        1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153,
        7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336,
    }
    return month_start[month] + day - 1

def dt_to_pydatetime(np_dt):
    """Convert numpy datetime64 to Python datetime."""
    return np_dt.astype('datetime64[us]').astype(datetime)

# Get baseline dates as Python datetimes
baseline_pydates = [dt_to_pydatetime(t) for t in baseline_times]
print(f"First baseline date: {baseline_pydates[0]}")
print(f"Last baseline date: {baseline_pydates[-1]}")

# Compute day of year for each baseline date
baseline_doy = np.array([day_of_year(d.month, d.day) for d in baseline_pydates])
print(f"Baseline DOY range: {baseline_doy.min()} to {baseline_doy.max()}")

# Identify baseline dates (1992-01-01 to 2002-12-31) within the extended period
# The extended period goes from 1991-12-27 to 2003-01-05
# Baseline: 1992-01-01 to 2002-12-31
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_in_range = np.array([(d >= baseline_start and d <= baseline_end) for d in baseline_pydates])
print(f"Number of baseline dates in range: {baseline_in_range.sum()}")

# For each day-of-year d (1-366, d != 60), the pool is all SST values whose date
# is within ±5 calendar days of a baseline date with that day of year.
# 
# Approach: For each baseline date t0 in [1992-01-01, 2002-12-31], it has some doy d.
# All dates t in [t0-5, t0+5] belong to pool d.
# Also, Feb 29 values belong to the windows of their calendar neighbours.
# So we need to figure out which dates in the extended baseline (1991-12-27 to 2003-01-05)
# are within ±5 days of which baseline dates.

# Let me build a mapping from date index to set of day-of-year pools it belongs to.
# For each date in the extended period, check which baseline dates are within ±5 days.

# First, build a list of (date, is_baseline, doy) for each date in extended period
all_pydates = baseline_pydates  # These are the dates in the extended period

# For each date in the extended period, find which day-of-year pools it belongs to
# A date t belongs to pool d if there's a baseline date t0 with doy(t0)=d and |t-t0|<=5
# (calendar days)

# For each d in 1-366 (except 60), find all dates in the extended period that belong to pool d
from collections import defaultdict

# For each day of year d, collect the indices of dates in the extended period that are in its pool
pool_dates = defaultdict(list)

# For each baseline date t0 (in 1992-01-01 to 2002-12-31), it has doy d
# All dates t in extended period with |t - t0| <= 5 days belong to pool d
# We can find these dates by scanning the extended period

for i, t0 in enumerate(all_pydates):
    if not baseline_in_range[i]:
        continue
    d = baseline_doy[i]
    # Find dates in extended period within ±5 days of t0
    t_start = t0 - timedelta(days=5)
    t_end = t0 + timedelta(days=5)
    # Use binary search or just check all
    for j, t in enumerate(all_pydates):
        if t_start <= t <= t_end:
            pool_dates[d].append(j)

print(f"Number of day-of-year pools: {len(pool_dates)}")
# Check a few
for d in [1, 59, 61, 153, 366]:
    dates = [all_pydates[j] for j in pool_dates[d]]
    print(f"Pool for doy {d}: {len(dates)} dates, first={dates[0]}, last={dates[-1]}")
