
import numpy as np
import datetime
import calendar

def doy_from_date(date):
    """Compute day of year 1-366 by month and day.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366."""
    month, day = date.month, date.day
    # Days before each month in a leap year (treating Feb as 29 days)
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[month - 1] + day - 1

# Test
for d in [(1,1), (1,31), (2,28), (2,29), (3,1), (3,31), (4,1), (6,1), (8,31), (12,31)]:
    date = datetime.date(2024, d[0], d[1])  # 2024 is leap year
    print(f"{d[0]}/{d[1]}: doy={doy_from_date(date)}")

# Verify
print()
# Non-leap year
for d in [(1,1), (2,28), (3,1), (12,31)]:
    date = datetime.date(2021, d[0], d[1])
    print(f"2021 {d[0]}/{d[1]}: doy={doy_from_date(date)}")

# Check a specific date
date = datetime.date(1992, 6, 1)
print(f"\n1992-06-01: doy={doy_from_date(date)}")
