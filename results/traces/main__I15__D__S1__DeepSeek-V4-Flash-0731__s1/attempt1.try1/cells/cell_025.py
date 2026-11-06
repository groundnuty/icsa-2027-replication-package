
import numpy as np
import datetime

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# For doy 153 (June 1), baseline dates are June 1 of 1992-2002
# Pool is ±5 days around each June 1
baseline_jun1 = [datetime.date(y, 6, 1) for y in range(1992, 2003)]
pool_dates = set()
for bdt in baseline_jun1:
    for i in range(-5, 6):
        pool_dates.add(bdt + datetime.timedelta(days=i))
pool_dates = sorted(pool_dates)
print(f"doy 153 (Jun 1): pool has {len(pool_dates)} dates")
print(f"First: {pool_dates[0]}, Last: {pool_dates[-1]}")
# Verify: May 27 to Jun 6 of each year 1992-2002
for d in pool_dates[:12]:
    print(f"  {d}: doy={date_to_doy(d)}")
