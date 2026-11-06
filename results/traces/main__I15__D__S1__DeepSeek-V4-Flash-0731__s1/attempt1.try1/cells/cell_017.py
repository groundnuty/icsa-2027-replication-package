
import numpy as np
import datetime
import pandas as pd

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

start = datetime.date(1991, 12, 27)
end = datetime.date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

doy_map = {dt: date_to_doy(dt) for dt in all_dates}

# Check doys around 59, 60, 61
for d_val in [58, 59, 60, 61, 62]:
    if d_val == 60:
        continue
    baseline_dates_with_doy = [dt for dt in all_dates 
                               if baseline_start <= dt <= baseline_end and doy_map[dt] == d_val]
    print(f"doy {d_val}: baseline dates:", baseline_dates_with_doy[:3], "...", baseline_dates_with_doy[-3:])
    pool_dates = set()
    for bdt in baseline_dates_with_doy:
        for i in range(-5, 6):
            dt2 = bdt + datetime.timedelta(days=i)
            if start <= dt2 <= end:
                pool_dates.add(dt2)
    print(f"  pool has {len(pool_dates)} dates")
    # Check if any Feb 29 dates are in these pools
    feb29 = [dt for dt in pool_dates if dt.month == 2 and dt.day == 29]
    print(f"  Feb 29 dates in pool: {feb29}")
