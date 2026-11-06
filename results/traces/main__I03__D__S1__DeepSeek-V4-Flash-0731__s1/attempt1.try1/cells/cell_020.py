
import numpy as np
import datetime as dt

# Load data (we'll keep everything in one script)
# Re-load from the previous state - actually let me just do everything in this cell

# Define day-of-year mapping
def day_of_year(date):
    month = date.month
    day = date.day
    cum_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_before[month - 1] + day

# Identify baseline dates within 1992-01-01 to 2002-12-31
baseline_dates_full = [dt.datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in times[baseline_idx]]
baseline_dates_dt = [d.date() for d in baseline_dates_full]

# Baseline date range: 1991-12-27 to 2003-01-05
# The "core" baseline dates are 1992-01-01 to 2002-12-31
core_start = dt.date(1992, 1, 1)
core_end = dt.date(2002, 12, 31)

# For each day of year d (1-366), find all dates in baseline_dates that are within
# ±5 calendar days of a core baseline date with day_of_year == d

# Build mapping from date to index in baseline_dates
date_to_idx = {}
for i, d in enumerate(baseline_dates_dt):
    date_to_idx[d] = i

# For each doy d, collect the indices of all baseline dates that should be in the pool
# For each core baseline date with doy==d, include dates in [date-5days, date+5days]
from collections import defaultdict

doy_to_core_dates = defaultdict(list)
for i, d in enumerate(baseline_dates_dt):
    if core_start <= d <= core_end:
        doy = day_of_year(d)
        doy_to_core_dates[doy].append(d)

# For each doy, find all indices that should be in the pool
doy_to_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = set()
    for core_date in doy_to_core_dates[doy]:
        for delta in range(-5, 6):
            date = core_date + dt.timedelta(days=delta)
            if date in date_to_idx:
                indices.add(date_to_idx[date])
    doy_to_indices[doy] = sorted(indices)

# Print some info
for doy in [1, 59, 61, 153, 244, 366]:
    print(f"Day of year {doy}: {len(doy_to_indices[doy])} dates in pool")
    if doy_to_indices[doy]:
        idxs = doy_to_indices[doy]
        print(f"  First: {baseline_dates_dt[idxs[0]]}, Last: {baseline_dates_dt[idxs[-1]]}")
