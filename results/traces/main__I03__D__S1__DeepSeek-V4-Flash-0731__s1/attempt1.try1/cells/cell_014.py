
import numpy as np
import datetime as dt

def day_of_year(date):
    """Map a date to day of year (1-366) using the specified convention.
    
    The mapping treats February as always having 29 days:
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60 (no Feb 29).
    """
    month = date.month
    day = date.day
    # Days before each month, assuming Feb has 29 days
    cum_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
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
    dt.date(2014, 6, 1),   # should be 31+29+31+30+31+1 = 153
    dt.date(2014, 8, 31),  # should be 31+29+31+30+31+30+31+31 = 244
]
for d in test_dates:
    print(f"{d}: {day_of_year(d)}")
