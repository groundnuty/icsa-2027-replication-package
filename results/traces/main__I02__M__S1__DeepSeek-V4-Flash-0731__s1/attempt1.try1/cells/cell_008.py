
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Baseline with window extension: 1991-12-27 to 2003-01-05
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)

# Target: 2004-06-01 to 2004-08-31
target_start = date(2004, 6, 1)
target_end = date(2004, 8, 31)

def doy_from_date(d):
    """Map a date to day of year 1-366."""
    month, day = d.month, d.day
    # Days before this month
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if month == 2 and day == 29:
        return 60
    if month > 2:
        # After Feb, add 1 for leap day
        # But wait, the mapping says Feb 28=59, Feb 29=60, Mar 1=61
        # In non-leap years, Mar 1 should also be 61
        # So the mapping is: Jan 1=1, ..., Jan 31=31, Feb 1=32, ..., Feb 28=59,
        # Feb 29=60 (leap only), Mar 1=61, ...
        # This means the cumulative days for each month are:
        # Jan: 0, Feb: 31, Mar: 59, Apr: 90, May: 120, Jun: 151,
        # Jul: 181, Aug: 212, Sep: 243, Oct: 273, Nov: 304, Dec: 334
        # And then for Mar onwards, we need to add 1 for the leap day
        # But the problem says non-leap years have no day 60
        # So the mapping must be: if month >= 3, add 1 to account for Feb 29
        # being counted in the fixed 366-day calendar
        pass
    
    # Let me just implement this directly:
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    # This is a fixed mapping based on the 366-day calendar
    # The cumulative days before each month:
    # Jan: 0, Feb: 31, Mar: 60, Apr: 91, May: 121, Jun: 152,
    # Jul: 182, Aug: 213, Sep: 244, Oct: 274, Nov: 305, Dec: 335
    
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month - 1] + day

# Test the mapping
print(f"Jan 1: {doy_from_date(date(1992,1,1))}")
print(f"Jan 31: {doy_from_date(date(1992,1,31))}")
print(f"Feb 28: {doy_from_date(date(1992,2,28))}")
print(f"Feb 29: {doy_from_date(date(1992,2,29))}")
print(f"Mar 1: {doy_from_date(date(1992,3,1))}")
print(f"Dec 31: {doy_from_date(date(1992,12,31))}")
print(f"Feb 28 (non-leap): {doy_from_date(date(1993,2,28))}")
print(f"Mar 1 (non-leap): {doy_from_date(date(1993,3,1))}")
