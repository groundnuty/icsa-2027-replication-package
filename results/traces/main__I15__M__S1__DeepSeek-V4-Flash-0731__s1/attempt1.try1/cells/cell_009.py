import numpy as np
from datetime import datetime, timedelta

# Function to compute day of year (1-366) as per the task definition
def day_of_year(date):
    """Map date to day of year 1-366. 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ... 31 Dec=366"""
    month = date.month
    day = date.day
    # Days in months before the given month (in the special calendar)
    # Jan=31, Feb=28 (or 29 if leap), Mar=31, Apr=30, May=31, Jun=30, Jul=31, Aug=31, Sep=30, Oct=31, Nov=30, Dec=31
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # But we need to handle Feb 29 specially
    # For a leap year: 29 Feb should map to 60
    # For a non-leap year, there is no day 60
    
    # Standard cumulative days: Jan=31, Feb=28, Mar=31, Apr=30, ...
    # If leap year and date >= Mar 1, add 1
    is_leap = (date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0)
    
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]  # days before month (non-leap)
    
    doy = cum_days[month - 1] + day
    if is_leap and month > 2:
        doy += 1
    
    return doy

# Test
print("1 Jan:", day_of_year(datetime(1992, 1, 1)))  # should be 1
print("28 Feb 1992:", day_of_year(datetime(1992, 2, 28)))  # should be 59
print("29 Feb 1992:", day_of_year(datetime(1992, 2, 29)))  # should be 60
print("1 Mar 1992:", day_of_year(datetime(1992, 3, 1)))  # should be 61
print("28 Feb 1993:", day_of_year(datetime(1993, 2, 28)))  # should be 59
print("1 Mar 1993:", day_of_year(datetime(1993, 3, 1)))  # should be 61
print("31 Dec 1992:", day_of_year(datetime(1992, 12, 31)))  # should be 366
print("31 Dec 1993:", day_of_year(datetime(1993, 12, 31)))  # should be 365
print("1 Mar 2000:", day_of_year(datetime(2000, 3, 1)))  # should be 61
