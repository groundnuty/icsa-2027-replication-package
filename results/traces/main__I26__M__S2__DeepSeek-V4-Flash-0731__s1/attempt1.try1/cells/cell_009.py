
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Define day-of-year mapping as per task
def day_of_year_custom(dt):
    """Map a date to day of year 1-366 using the task's convention.
    Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, ..., Dec 31 = 366"""
    month = dt.month
    day = dt.day
    # Days in each month assuming leap year (Feb has 29)
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Test
test_dates = [
    date(1992, 1, 1),
    date(1992, 2, 28),
    date(1992, 2, 29),
    date(1992, 3, 1),
    date(1992, 12, 31),
    date(1993, 1, 1),
    date(1993, 2, 28),
    date(1993, 3, 1),  # non-leap year, March 1 should be 61
]
for d in test_dates:
    print(f"{d}: doy = {day_of_year_custom(d)}")

# Verify: Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, Dec 31 = 366
assert day_of_year_custom(date(1992, 1, 1)) == 1
assert day_of_year_custom(date(1992, 2, 28)) == 59
assert day_of_year_custom(date(1992, 2, 29)) == 60
assert day_of_year_custom(date(1992, 3, 1)) == 61
assert day_of_year_custom(date(1992, 12, 31)) == 366
assert day_of_year_custom(date(1993, 3, 1)) == 61  # non-leap, still 61
print("\nDay-of-year mapping verified.")
