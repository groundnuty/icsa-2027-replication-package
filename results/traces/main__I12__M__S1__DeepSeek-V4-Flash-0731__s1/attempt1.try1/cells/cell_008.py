
from datetime import date, timedelta

def day_of_year(d):
    """Map date to day of year 1-366 by month and day."""
    month = d.month
    day = d.day
    # Days before this month
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Feb 29 maps to 60, and Feb 28 maps to 59
    # So the mapping is: 1 Jan = 1, ..., 31 Jan = 31, 1 Feb = 32, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ...
    doy = sum(days_in_month[:month]) + day
    # But this gives Feb 28 = 31+28 = 59, Feb 29 = 31+29 = 60, Mar 1 = 31+28+1 = 60 which is wrong.
    # We need Mar 1 = 61.
    if month > 2:
        # March onwards: add 1 more day to account for the special Feb 29 = 60 mapping
        # In non-leap years, we still use the fixed mapping where Mar 1 = 61
        # Actually, the mapping is fixed regardless of year:
        # Feb has 28 days normally (giving Feb 28 = 59), but Feb 29 = 60 in leap years.
        # So the mapping for months >= 3 should add one extra day.
        doy = sum(days_in_month[:month]) + day + 1
    return doy

# Verify
print("Jan 1:", day_of_year(date(1992, 1, 1)))  # should be 1
print("Feb 28:", day_of_year(date(1992, 2, 28)))  # should be 59
print("Feb 29:", day_of_year(date(1992, 2, 29)))  # should be 60
print("Mar 1:", day_of_year(date(1992, 3, 1)))  # should be 61
print("Dec 31:", day_of_year(date(1992, 12, 31)))  # should be 366

# Check non-leap year
print("Mar 1 1993:", day_of_year(date(1993, 3, 1)))  # should be 61
print("Feb 28 1993:", day_of_year(date(1993, 2, 28)))  # should be 59
