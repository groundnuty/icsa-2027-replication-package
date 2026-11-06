
import numpy as np
from datetime import datetime, timedelta

days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_date(dt):
    return days_before_month[dt.month - 1] + dt.day

base_start = datetime(1991, 12, 27)
base_end = datetime(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)

baseline_dates = [dt for dt in all_dates if datetime(1992,1,1) <= dt <= datetime(2002,12,31)]

# Check doy 366 (Dec 31)
doy366_baseline = [b for b in baseline_dates if doy_from_date(b) == 366]
print("Baseline dates with doy 366:", [b.date().isoformat() for b in doy366_baseline])

pool_366 = set()
for b in doy366_baseline:
    for i in range(-5, 6):
        pool_366.add(b + timedelta(days=i))
pool_366_in_range = sorted([d for d in pool_366 if base_start <= d <= base_end])
print("Pool dates for doy 366:", len(pool_366_in_range))
# Check if 2003-01-01 through 2003-01-05 are in the pool
print("Dates in 2003:", [d.date().isoformat() for d in pool_366_in_range if d.year == 2003])
