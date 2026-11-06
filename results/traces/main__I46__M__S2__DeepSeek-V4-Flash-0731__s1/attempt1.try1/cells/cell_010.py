
import numpy as np
from datetime import date, timedelta

# Day-of-year mapping
def doy_from_month_day(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

doy_to_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    dates_set = set()
    for bd in baseline_dates:
        if doy_from_month_day(bd.month, bd.day) == doy:
            for offset in range(-5, 6):
                dates_set.add(bd + timedelta(days=offset))
    doy_to_dates[doy] = sorted(dates_set)

# Check all dates are within extended range
ext_start = date(1991, 12, 27)
ext_end = date(2003, 1, 5)
all_ok = True
for doy, dates in doy_to_dates.items():
    for dt in dates:
        if dt < ext_start or dt > ext_end:
            print(f"Day {doy}: date {dt} outside extended range")
            all_ok = False
print("All dates in extended range:", all_ok)

# Also check for days that might have missing coverage
for doy in range(1, 367):
    if doy == 60:
        continue
    dates = doy_to_dates[doy]
    if len(dates) != 121:
        print(f"Day {doy}: only {len(dates)} dates")

# Check day 60 (Feb 29) - it should not have a pool
print("Day 60 in doy_to_dates:", 60 in doy_to_dates)
