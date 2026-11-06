
import numpy as np
import datetime as dt
import xarray as xr

# Define the day-of-year mapping function
def day_of_year(date):
    """Map a date to day of year (1-366) using the specified convention."""
    month = date.month
    day = date.day
    # Days in months before the given month (non-leap)
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = cum_days[month - 1] + day
    # If leap year and after Feb 28, add 1 (but we use the special mapping)
    # Actually the task says: 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, etc.
    # This is just the cumulative day count regardless of leap year!
    # So March 1 is always 61, even in non-leap years.
    # That means the mapping is simply: doy = cumulative_days[month-1] + day
    # where cumulative_days uses 31, 28, 31, ... (non-leap month lengths)
    return doy

# Test
test_dates = [
    dt.date(1992, 1, 1),   # should be 1
    dt.date(1992, 2, 28),  # should be 59
    dt.date(1992, 2, 29),  # should be 60
    dt.date(1992, 3, 1),   # should be 61
    dt.date(1992, 12, 31), # should be 366
    dt.date(1993, 2, 28),  # should be 59 (non-leap, no day 60)
    dt.date(1993, 3, 1),   # should be 61
]
for d in test_dates:
    print(f"{d}: {day_of_year(d)}")
