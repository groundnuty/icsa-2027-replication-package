
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

# All loaded dates
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_loaded_dates = []
d = start
while d <= end:
    all_loaded_dates.append(d)
    d += timedelta(days=1)
n_loaded = len(all_loaded_dates)

# For each day d (1-366, d≠60), find indices in all_loaded_dates that belong to pool d
# Pool d = { x : ∃ baseline y ∈ [1992-01-01, 2002-12-31] with doy(y)=d and |x-y| ≤ 5 days }

# Precompute doy for all loaded dates
loaded_doy = [day_of_year(dt) for dt in all_loaded_dates]

# For each loaded date x, the days d it contributes to are:
# For each y in [x-5, x+5] ∩ [1992-01-01, 2002-12-31], d = doy(y)
# But actually, we need to check if y is a baseline date (in [1992-01-01, 2002-12-31]) 
# AND doy(y) = d.

# A simpler approach: for each day d, iterate over baseline dates with doy=d and their windows.

# But that could be slow. Let me think of a better approach.

# For a given day d (month m, day day_of_month):
# The baseline dates with doy=d are: for each year in 1992-2002, the date (year, m, day).
# Their ±5 day windows cover dates from (1992, m, day)-5 to (2002, m, day)+5.
# Since windows from different years don't overlap (they're in different years),
# the pool for d covers specific date ranges each year.

# Actually, let me just build a boolean mask for each day d.
# This is more straightforward.

# For each day d from 1 to 366 (d≠60), find which loaded dates are in the pool.
# I'll build a mapping: pool_indices[d] = list of indices in all_loaded_dates

# Method: For each baseline date y (in [1992-01-01, 2002-12-31]):
#   d = doy(y)
#   For each date x in [y-5, y+5]:
#     if x is in all_loaded_dates, add its index to pool_indices[d]

# Let me implement this.
pool_indices = defaultdict(set)

baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Create a dict mapping date to index in all_loaded_dates
date_to_idx = {dt: i for i, dt in enumerate(all_loaded_dates)}

# Iterate over all baseline dates
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy != 60:  # day 60 gets no pool
        # For this baseline date, the window is [d-5, d+5]
        for offset in range(-5, 6):
            x = d + timedelta(days=offset)
            if x in date_to_idx:
                pool_indices[doy].add(date_to_idx[x])
    d += timedelta(days=1)

# Print some statistics
print("Number of days with pools:", len(pool_indices))
print("Pool sizes for some days:")
for day in [1, 59, 61, 153, 244, 366]:
    if day in pool_indices:
        print(f"  Day {day}: {len(pool_indices[day])} dates")
print("Day 60 pool:", "None" if 60 not in pool_indices else f"{len(pool_indices[60])} dates")

# Verify: day 1 pool should include dates from 1991-12-27 to 2003-01-06 but capped at 2003-01-05
# Day 1 baseline dates: Jan 1 of each year 1992-2002 (11 dates)
# Windows: Dec 27 to Jan 6 for each year
# 1992: Dec 27, 1991 to Jan 6, 1992
# ...
# 2002: Dec 27, 2001 to Jan 6, 2002
# But Dec 27, 1991 to Dec 31, 1991 are outside [1992-01-01, 2002-12-31] but the task says to include them.
# And Jan 1 to Jan 5, 2003 are also included.

# So day 1 pool should include:
# 1991-12-27 to 1992-01-06 (but 1992-01-06 is within baseline)
# 1992-12-27 to 1993-01-06
# ...
# 2001-12-27 to 2002-01-06
# 2002-12-27 to 2003-01-06 (but 2003-01-06 is beyond our loaded data, which ends at 2003-01-05)
# Wait, our loaded data goes to 2003-01-05. The window for Jan 1, 2002 would be Dec 27, 2002 to Jan 6, 2003.
# Jan 6, 2003 is beyond our loaded data, so it's not included.

# Actually wait, the task says: "Windows near the ends of the baseline reach up to 5 days beyond it 
# (1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); include those days."
# So we should include 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05.

# Let me check: for day 1 (Jan 1), the baseline date Jan 1, 1992 has a window from Dec 27, 1991 to Jan 6, 1992.
# Dec 27-31, 1991 are outside the baseline but should be included per the task instructions.
# Similarly, Jan 1, 2002 has a window from Dec 27, 2002 to Jan 6, 2003.
# Jan 1-5, 2003 are outside the baseline but should be included.

# Our loaded data covers 1991-12-27 to 2003-01-05, so we should have all of these.
# The pool for day 1 should have 11 windows × 11 days = 121 dates, minus the ones beyond our data range.

# Let me verify
day1_pool = sorted(pool_indices[1])
print(f"\nDay 1 pool: {len(day1_pool)} dates")
print("First few:", [all_loaded_dates[i].strftime('%Y-%m-%d') for i in day1_pool[:5]])
print("Last few:", [all_loaded_dates[i].strftime('%Y-%m-%d') for i in day1_pool[-5:]])

# Check if 1991-12-27 is in the pool for day 1
idx = date_to_idx.get(datetime(1991, 12, 27))
print(f"1991-12-27 in day 1 pool: {idx in pool_indices[1] if idx is not None else 'not in data'}")
idx = date_to_idx.get(datetime(2003, 1, 5))
print(f"2003-01-05 in day 1 pool: {idx in pool_indices[1] if idx is not None else 'not in data'}")
