
import numpy as np
import datetime
import pandas as pd

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

# Generate all dates from 1991-12-27 to 2003-01-05
start = datetime.date(1991, 12, 27)
end = datetime.date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

print("Total dates in range:", len(all_dates))

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

# For each date, compute its doy
doy_map = {}
for dt in all_dates:
    doy = date_to_doy(dt)
    if dt.year == 1992 and dt.month == 2 and dt.day == 29:
        # Feb 29 1992 maps to doy 60
        pass
    doy_map[dt] = doy

# For each doy d (1-366, excluding 60), find which dates are in its pool
# A date dt' is in pool for doy d if there exists a baseline date dt (1992-2002) with doy(dt)=d
# such that |dt' - dt| <= 5 days

pools = {}  # doy -> list of dates
for d_val in range(1, 367):
    if d_val == 60:
        continue
    # Find all baseline dates with this doy
    baseline_dates_with_doy = [dt for dt in all_dates 
                               if baseline_start <= dt <= baseline_end and doy_map[dt] == d_val]
    pool_dates = set()
    for bdt in baseline_dates_with_doy:
        for i in range(-5, 6):
            dt2 = bdt + datetime.timedelta(days=i)
            if start <= dt2 <= end:
                pool_dates.add(dt2)
    pools[d_val] = sorted(pool_dates)
    if d_val <= 5 or d_val >= 360:
        print(f"doy {d_val}: {len(pool_dates)} dates, first={sorted(pool_dates)[0]}, last={sorted(pool_dates)[-1]}")
