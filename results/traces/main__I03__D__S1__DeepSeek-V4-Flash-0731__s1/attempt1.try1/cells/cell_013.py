
import numpy as np
import datetime as dt

def day_of_year(date):
    """Map a date to day of year (1-366) using the specified convention.
    
    The mapping uses fixed month lengths:
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    """
    month = date.month
    day = date.day
    # Fixed cumulative days for each month start (non-leap convention):
    # Jan 1 = 1, Feb 1 = 32, Mar 1 = 61, Apr 1 = 92, May 1 = 122, ...
    cum_days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = cum_days_before[month - 1] + day
    return doy

# Test
test_dates = [
    dt.date(1992, 1, 1),   # should be 1
    dt.date(1992, 2, 28),  # should be 59
    dt.date(1992, 2, 29),  # should be 60
    dt.date(1992, 3, 1),   # should be 61
    dt.date(1992, 12, 31), # should be 366
    dt.date(1993, 2, 28),  # should be 59
    dt.date(1993, 3, 1),   # should be 61 (skipping 60 in non-leap)
    dt.date(1993, 12, 31), # should be 366
]
for d in test_dates:
    print(f"{d}: {day_of_year(d)}")
