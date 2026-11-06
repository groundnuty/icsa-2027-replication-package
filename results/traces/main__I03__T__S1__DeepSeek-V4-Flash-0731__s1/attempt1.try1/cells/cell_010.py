
import numpy as np
import datetime
from calendar import monthrange

def day_of_year(m, d):
    """Map (month, day) to day of year 1-366 as if every year is leap."""
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    # month_offsets[m] = sum of days in months 1..(m-1) counting Feb as 29
    return month_offsets[m] + d

# Verify
print("Jan 1:", day_of_year(1,1))  # should be 1
print("Feb 28:", day_of_year(2,28))  # should be 59
print("Feb 29:", day_of_year(2,29))  # should be 60
print("Mar 1:", day_of_year(3,1))  # should be 61
print("Dec 31:", day_of_year(12,31))  # should be 366
print("Jun 1:", day_of_year(6,1))  # 152+1=153
print("Aug 31:", day_of_year(8,31))  # 213+31=244

# Check all months
for m in range(1, 13):
    if m == 2:
        days = 29
    elif m in [4, 6, 9, 11]:
        days = 30
    else:
        days = 31
    print(f"Month {m}: day 1 -> {day_of_year(m,1)}, day {days} -> {day_of_year(m,days)}")
