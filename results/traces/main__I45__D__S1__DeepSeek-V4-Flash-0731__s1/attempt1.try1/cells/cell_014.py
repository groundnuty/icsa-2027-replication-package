
import numpy as np
from datetime import datetime, timedelta

def day_of_year(year, month, day):
    """Map a date to day of year 1-366."""
    # Non-leap year month offsets
    month_offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # For leap years, February has 29 days
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    
    if month > 2 and is_leap:
        return month_offsets[month-1] + day + 1  # +1 for Feb 29
    else:
        return month_offsets[month-1] + day

# Test
print("Jan 1:", day_of_year(1992, 1, 1))  # Should be 1
print("Feb 28:", day_of_year(1992, 2, 28))  # Should be 59
print("Feb 29:", day_of_year(1992, 2, 29))  # Should be 60
print("Mar 1:", day_of_year(1992, 3, 1))  # Should be 61
print("Dec 31:", day_of_year(1992, 12, 31))  # Should be 366

# Test non-leap
print("Feb 28 (non-leap):", day_of_year(1993, 2, 28))  # 59
print("Mar 1 (non-leap):", day_of_year(1993, 3, 1))  # 60 (but non-leap has no day 60)
