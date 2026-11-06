
import numpy as np
import pandas as pd

# Let me figure out the day-of-year mapping as described
# 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
# Non-leap years have no day 60

def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

# Test the mapping for a few dates
# For a leap year: 2016
dates = pd.date_range('2016-01-01', '2016-12-31')
for d in ['2016-01-01', '2016-02-28', '2016-02-29', '2016-03-01', '2016-12-31']:
    dt = pd.Timestamp(d)
    # Compute day of year according to the task's mapping
    # Months: Jan=31, Feb=29 (leap), Mar=31, Apr=30, May=31, Jun=30, Jul=31, Aug=31, Sep=30, Oct=31, Nov=30, Dec=31
    month_days_leap = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days_leap[:dt.month]) + dt.day
    print(d, "->", doy)

print("---")
# For a non-leap year: 2015
for d in ['2015-01-01', '2015-02-28', '2015-03-01', '2015-12-31']:
    dt = pd.Timestamp(d)
    month_days_nonleap = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days_nonleap[:dt.month]) + dt.day
    print(d, "->", doy)
