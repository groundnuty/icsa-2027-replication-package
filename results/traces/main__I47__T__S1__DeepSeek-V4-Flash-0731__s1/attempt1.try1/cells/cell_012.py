
import numpy as np
from datetime import datetime, timedelta

# First, define the day-of-year mapping
def day_of_year(month, day):
    """Map month/day to day-of-year 1-366."""
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Handle Feb 29 specially
    if month == 2 and day == 29:
        return 60
    # Standard cumulative days
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:  # For months after Feb, add 1 since Feb has 29 in this mapping
        doy += 1
    return doy

# Test
print(day_of_year(1, 1))   # Should be 1
print(day_of_year(2, 28))  # Should be 59
print(day_of_year(2, 29))  # Should be 60
print(day_of_year(3, 1))   # Should be 61
print(day_of_year(12, 31)) # Should be 366
print(day_of_year(6, 1))   # Should be 153
print(day_of_year(8, 31))  # Should be 244

# Check: sum of days for Jan through Nov + Dec 31
# Jan: 31, Feb: 29, Mar: 31, Apr: 30, May: 31, Jun: 30, Jul: 31, Aug: 31, Sep: 30, Oct: 31, Nov: 30
# So Dec 31 = 31+29+31+30+31+30+31+31+30+31+30+31 = 366
print(31+29+31+30+31+30+31+31+30+31+30+31)
