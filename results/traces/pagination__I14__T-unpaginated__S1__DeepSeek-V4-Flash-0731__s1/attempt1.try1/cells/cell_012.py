
import numpy as np
from datetime import date, timedelta

def day_of_year_fixed(y, m, d):
    """Map a date to day of year 1-366 as per the task spec."""
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    else:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

# Build all baseline dates with their day-of-year
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# For each day-of-year d (1-366, d != 60), build the pool
# The pool for day d is the set of calendar dates X such that there exists
# a baseline date B (1992-01-01 to 2002-12-31) with day_of_year(B) = d and |X - B| <= 5

# For each date in the full range, determine which day-of-year pools it belongs to
# We need to include dates from 1991-12-27 to 2003-01-05

# Strategy: for each baseline date B with day-of-year d, mark all dates within ±5 days as belonging to pool d

# First, identify baseline dates by day-of-year
baseline_dates_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year_fixed(d.year, d.month, d.day)
    if doy != 60:  # Day 60 gets no pool of its own
        if doy not in baseline_dates_by_doy:
            baseline_dates_by_doy[doy] = []
        baseline_dates_by_doy[doy].append(d)
    d += timedelta(days=1)

# Now for each day-of-year, find the set of dates in the pool
# We only need to track which dates (from 1991-12-27 to 2003-01-05) belong to each pool
full_range_start = date(1991, 12, 27)
full_range_end = date(2003, 1, 5)

# For efficiency, let's map each date in the full range to an index
all_dates = []
d = full_range_start
while d <= full_range_end:
    all_dates.append(d)
    d += timedelta(days=1)
n_dates = len(all_dates)
date_to_idx = {d: i for i, d in enumerate(all_dates)}

# For each day-of-year, collect indices of dates in its pool
pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = set()
    for bd in baseline_dates_by_doy.get(doy, []):
        for offset in range(-5, 6):
            nd = bd + timedelta(days=offset)
            if full_range_start <= nd <= full_range_end:
                indices.add(date_to_idx[nd])
    pool_indices[doy] = sorted(indices)

# Print stats
for doy in [1, 59, 60, 61, 182, 183, 366]:
    if doy != 60:
        print(f"Day-of-year {doy}: {len(pool_indices[doy])} dates in pool")
        if len(pool_indices[doy]) > 0:
            first_date = all_dates[pool_indices[doy][0]]
            last_date = all_dates[pool_indices[doy][-1]]
            print(f"  Range: {first_date} to {last_date}")
            print(f"  First few dates: {[all_dates[i].isoformat() for i in pool_indices[doy][:3]]}")

# Check: pool for day 1 should include dates from 1991-12-27 to 2002-01-06
# (each Jan 1 from 1992-2002 ±5 days)
print(f"\nPool for day 1: {len(pool_indices[1])} dates")
print(f"  First 10: {[all_dates[i].isoformat() for i in pool_indices[1][:10]]}")
print(f"  Last 10: {[all_dates[i].isoformat() for i in pool_indices[1][-10:]]}")
