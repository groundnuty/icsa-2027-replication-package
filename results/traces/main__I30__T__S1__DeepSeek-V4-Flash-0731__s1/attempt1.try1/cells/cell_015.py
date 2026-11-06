
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta

# Day of year mapping as specified
def day_of_year(year, month, day):
    """Map date to day of year 1-366."""
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    if month == 1:
        return day
    if month == 2:
        return 31 + day
    # March onwards
    # Days in Jan + Feb (depending on leap)
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    feb_days = 29 if is_leap else 28
    days_before = 31 + feb_days
    # days in months before current
    month_days = [31, feb_days, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:month-1]) + day
    return doy

# Test
print(day_of_year(1992, 1, 1))   # should be 1
print(day_of_year(1992, 2, 28))  # should be 59
print(day_of_year(1992, 2, 29))  # should be 60
print(day_of_year(1992, 3, 1))   # should be 61
print(day_of_year(1992, 12, 31)) # should be 366
print(day_of_year(1993, 2, 28))  # should be 59
print(day_of_year(1993, 3, 1))   # should be 61
# Non-leap year: no day 60
# Verify: 1993 has 365 days, 1 Mar should be day 61
