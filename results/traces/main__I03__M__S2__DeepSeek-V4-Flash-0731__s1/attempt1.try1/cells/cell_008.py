
import numpy as np
from datetime import datetime, date, timedelta

def day_of_year(month, day):
    """Map month/day to day of year 1-366 as specified."""
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Test
print("Jan 1:", day_of_year(1, 1))
print("Feb 28:", day_of_year(2, 28))
print("Feb 29:", day_of_year(2, 29))
print("Mar 1:", day_of_year(3, 1))
print("Dec 31:", day_of_year(12, 31))
