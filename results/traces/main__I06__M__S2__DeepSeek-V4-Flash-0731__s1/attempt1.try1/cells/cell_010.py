
import numpy as np
import pandas as pd

def doy_from_date(dt):
    """Map a datetime to day-of-year 1-366 based on month/day."""
    return doy_from_md(dt.month, dt.day)

def doy_from_md(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

# All baseline dates in 1992-2002
baseline_dates = pd.date_range('1992-01-01', '2002-12-31', freq='D')

# For each day-of-year d (except 60), find pool dates
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    # Find baseline dates with this day-of-year
    b_dates = [dt for dt in baseline_dates if doy_from_date(dt) == d]
    # For each, extend ±5 days
    pool_dates = set()
    for b in b_dates:
        for i in range(-5, 6):
            pool_dates.add(b + pd.Timedelta(days=i))
    pools[d] = sorted(pool_dates)

# Check sizes
print("Pool sizes for sample days:")
for d in [1, 59, 61, 153, 182, 183, 244, 366]:
    print(f"  Day {d}: {len(pools[d])} dates, first={pools[d][0]}, last={pools[d][-1]}")
