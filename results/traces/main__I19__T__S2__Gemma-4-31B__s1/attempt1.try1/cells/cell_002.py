import xarray as xr
import fsspec
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

def get_day_of_year(dt):
    """Maps a date to day of year 1-366 as specified."""
    month = dt.month
    day = dt.day
    # Cumulative days for non-leap years
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = cum_days[month-1] + day
    if month > 2:
        # If it's after February, we must account for the gap at day 60
        # In this specific mapping: 1 Mar = 61. 
        # In non-leap years, Feb 28 (59) is followed by Mar 1.
        # To make Mar 1 = 61, we add 1 to all dates from Mar 1 onwards.
        doy += 1
    return doy

# Actually, let's check if a simpler logic works:
# Jan: 1-31
# Feb: 32-59
# Feb 29: 60
# Mar 1: 61
# ...
# Dec 31: 366
# This is exactly: day_of_year if month <= 2 else day_of_year + 1 (using standard doy)
# wait, standard doy for Mar 1 in non-leap is 60. In leap it's 61.
# In this mapping, Mar 1 is ALWAYS 61.
# Let's test:
# Non-leap: Mar 1 is doy 60. Mapping: 60 + 1 = 61.
# Leap: Mar 1 is doy 61. Mapping: 61? No.
# Let's use a manual table.

def get_doy_custom(dt):
    month = dt.month
    day = dt.day
    # days before the start of the month
    month_starts = {
        1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151, 
        7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334
    }
    # This table is for non-leap.
    # If month <= 2, the doy is just month_starts[month] + day.
    # If month > 2, it's month_starts[month] + day + 1.
    # Let's verify:
    # Jan 1: 0 + 1 = 1.
    # Feb 28: 31 + 28 = 59.
    # Feb 29: (not covered by this) - we handle it separately.
    # Mar 1: 59 + 1 + 1 = 61. Correct.
    # Dec 31: 334 + 31 + 1 = 366. Correct.
    if month == 2 and day == 29:
        return 60
    if month <= 2:
        return month_starts[month] + day
    else:
        return month_starts[month] + day + 1

# Testing
for d in [datetime(2014, 1, 1), datetime(2014, 2, 28), datetime(2014, 3, 1), datetime(2014, 12, 31), datetime(2012, 2, 29)]:
    print(f"{d.date()} -> {get_doy_custom(d)}")

