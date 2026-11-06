
import numpy as np
from datetime import date, timedelta

# Function to compute day of year (1-366)
def day_of_year(y, m, d):
    """Map a date to day of year 1-366 as per the task spec."""
    # Days in each month for non-leap year
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check if leap year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    
    if is_leap:
        days_in_month[1] = 29
    
    doy = sum(days_in_month[:m-1]) + d
    return doy

# Verify
print(f"1 Jan 2000: {day_of_year(2000, 1, 1)}")  # Should be 1
print(f"28 Feb 2000: {day_of_year(2000, 2, 28)}")  # Should be 59
print(f"29 Feb 2000: {day_of_year(2000, 2, 29)}")  # Should be 60
print(f"1 Mar 2000: {day_of_year(2000, 3, 1)}")  # Should be 61
print(f"31 Dec 2000: {day_of_year(2000, 12, 31)}")  # Should be 366
print(f"28 Feb 2001: {day_of_year(2001, 2, 28)}")  # Should be 59
print(f"1 Mar 2001: {day_of_year(2001, 3, 1)}")  # Should be 61
print(f"31 Dec 2001: {day_of_year(2001, 12, 31)}")  # Should be 365
