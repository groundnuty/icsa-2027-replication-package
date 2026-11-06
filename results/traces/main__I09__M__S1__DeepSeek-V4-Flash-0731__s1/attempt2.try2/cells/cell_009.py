
from datetime import date, timedelta
import numpy as np

# Day-of-year mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

def doy_to_date_in_year(doy, year):
    for m in range(12):
        if doy <= cum_days[m] + month_days[m]:
            day = doy - cum_days[m]
            try:
                return date(year, m+1, day)
            except ValueError:
                return None
    return None

# For each doy d (1-366, except 60), find all pool dates
# Pool dates: all dates within ±5 days of a baseline date (1992-2002) with doy d
# Also include padding days: 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05

baseline_years = list(range(1992, 2003))  # 1992-2002

# Let's compute pool dates for a few test day-of-years
for test_doy in [1, 59, 60, 61, 200, 366]:
    pool_dates = []
    for y in baseline_years:
        d_base = doy_to_date_in_year(test_doy, y)
        if d_base is None:
            continue
        for offset in range(-5, 6):
            pool_dates.append(d_base + timedelta(days=offset))
    # Remove duplicates (shouldn't be any since windows don't overlap)
    pool_dates = sorted(set(pool_dates))
    print(f"doy {test_doy}: {len(pool_dates)} pool dates, first={pool_dates[0]}, last={pool_dates[-1]}")
    if test_doy == 1:
        print(f"  First few: {pool_dates[:15]}")
