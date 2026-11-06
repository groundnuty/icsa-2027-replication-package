import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_doy(dt):
    """Map date to day of year 1-366 as per requirements."""
    month = dt.month
    day = dt.day
    # Days per month for non-leap year
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    if month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        # Not needed if we just use fixed mapping.
        # The rule is: 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
        # This means the mapping is based on the calendar date, NOT the relative day of the year.
        pass
    # Fixed mapping based on month and day:
    # Jan: 1-31
    # Feb: 32-59 (Feb 28 is 59)
    # Feb 29: 60
    # Mar: 61-91 (Mar 1 is 61)
    # ...
    return doy

def get_fixed_doy(dt):
    month = dt.month
    day = dt.day
    # Mapping:
    # Jan 31 -> 31
    # Feb 28 -> 59
    # Feb 29 -> 60
    # Mar 1 -> 61
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # The problem is 29 Feb.
    # For non-leap years, we skip 60.
    # For leap years, 29 Feb is 60.
    # Let's use a dictionary for month-start days in a leap year.
    leap_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    
    # Wait, the prompt says:
    # 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366.
    # Non-leap years have no day 60.
    # This means:
    # If month == 1: doy = day
    # If month == 2: doy = 31 + day
    # If month >= 3:
    #   if the date is in a leap year and we are after Feb 29:
    #   Wait, just use the leap year mapping always.
    #   Jan: 1-31
    #   Feb: 32-60 (Feb 29 is 60)
    #   Mar: 61-91
    #   ...
    #   If it's a non-leap year, Feb 29 simply doesn't occur.
    
    # Let's use the mapping for a leap year:
    leap_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    # This is not quite right because Feb 28 should be 59.
    # If month == 2: return 31 + day. (Feb 28 -> 59, Feb 29 -> 60)
    # If month >= 3:
    #   The number of days before March is 31 + 29 = 60.
    #   So March 1 is 61.
    #   The number of days before April is 31 + 29 + 31 = 91.
    
    if month == 1: return day
    if month == 2: return 31 + day
    # For month >= 3, the offset is 60 (treating Feb as 29 days)
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[month-1] + day

# Verify the mapping
import datetime
test_dates = [datetime.date(2014, 1, 1), datetime.date(2014, 2, 28), 
              datetime.date(2016, 2, 29), datetime.date(2014, 3, 1), 
              datetime.date(2014, 12, 31)]
for d in test_dates:
    print(f"{d} -> {get_fixed_doy(d)}")

# Expected: 2014-01-01 -> 1, 2014-02-28 -> 59, 2016-02-29 -> 60, 2014-03-01 -> 61, 2014-12-31 -> 366
