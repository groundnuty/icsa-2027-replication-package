
import numpy as np
from datetime import datetime, timedelta

def day_of_year(dt):
    """Map a date to day of year 1-366."""
    month = dt.month
    day = dt.day
    # Days before month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Check if leap year
    is_leap = (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0)
    
    doy = sum(days_in_month[:month-1]) + day
    # After Feb in leap year, add 1
    if is_leap and month > 2:
        doy += 1
    
    return doy

# Test
print("Jan 1:", day_of_year(datetime(2000, 1, 1)))
print("Feb 28 (non-leap):", day_of_year(datetime(2001, 2, 28)))
print("Feb 28 (leap):", day_of_year(datetime(2000, 2, 28)))
print("Feb 29 (leap):", day_of_year(datetime(2000, 2, 29)))
print("Mar 1 (non-leap):", day_of_year(datetime(2001, 3, 1)))
print("Mar 1 (leap):", day_of_year(datetime(2000, 3, 1)))
print("Dec 31:", day_of_year(datetime(2000, 12, 31)))
print("Dec 31 (non-leap):", day_of_year(datetime(2001, 12, 31)))
