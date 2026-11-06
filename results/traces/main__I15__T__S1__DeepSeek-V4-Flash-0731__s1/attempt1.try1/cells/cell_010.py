import numpy as np
import xarray as xr
import fsspec
import json
import os
from datetime import datetime, timedelta

# First, let me understand the date-to-doy mapping
def date_to_doy(year, month, day):
    """Convert date to day of year (1-366). Non-leap years have no day 60."""
    # Check if leap year
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    # Days in each month (non-leap)
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    
    if is_leap and month > 2:
        return cum_days[month-1] + 1 + day
    else:
        return cum_days[month-1] + day

# Test the mapping
test_cases = [
    (1992, 1, 1, 1),
    (1992, 2, 28, 59),
    (1992, 2, 29, 60),  # 1992 is a leap year
    (1992, 3, 1, 61),
    (1992, 12, 31, 366),
    (1993, 1, 1, 1),
    (1993, 2, 28, 59),
    (1993, 3, 1, 61),  # Non-leap, so Mar 1 = day 61
    (1993, 12, 31, 365),
]

for y, m, d, expected in test_cases:
    result = date_to_doy(y, m, d)
    print(f"{y}-{m:02d}-{d:02d} -> doy {result} (expected {expected}) {'OK' if result == expected else 'FAIL'}")
