
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

# For each day d in 1-366 (d≠60), build a list of baseline dates y (in [1992-01-01, 2002-12-31])
# such that doy(y) = d.

# Let me find all baseline dates with each day-of-year
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Precompute all baseline dates
all_dates = []
d = baseline_start
while d <= baseline_end:
    all_dates.append(d)
    d += timedelta(days=1)

# Group by day of year
from collections import defaultdict
doy_to_dates = defaultdict(list)
for dt in all_dates:
    doy = day_of_year(dt)
    doy_to_dates[doy].append(dt)

print("Number of days with at least one date:", len(doy_to_dates))
print("Days 1-5:", [f"d={k}: {len(v)} dates" for k, v in sorted(doy_to_dates.items())[:5]])
print("Day 59:", len(doy_to_dates.get(59, [])), "dates")
print("Day 60:", len(doy_to_dates.get(60, [])), "dates")
print("Day 61:", len(doy_to_dates.get(61, [])), "dates")

# Verify: day 60 should have 3 dates (leap years 1992, 1996, 2000 in 1992-2002)
# Wait, 2000 is a leap year, so 1992, 1996, 2000 = 3 leap years
print("Day 60 dates:", [dt.strftime('%Y-%m-%d') for dt in doy_to_dates.get(60, [])])
