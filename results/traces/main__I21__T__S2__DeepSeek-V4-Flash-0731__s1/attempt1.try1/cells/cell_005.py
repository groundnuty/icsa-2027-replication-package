
import numpy as np
from datetime import datetime, timedelta

def day_of_year(dt):
    """Map a date to day of year 1-366 by month and day (Feb always has 29 days)."""
    month = dt.month
    day = dt.day
    # Cumulative days before each month, assuming Feb has 29 days
    # Jan: 0, Feb: 31, Mar: 60, Apr: 91, May: 121, Jun: 152, Jul: 182, Aug: 213, Sep: 244, Oct: 274, Nov: 305, Dec: 335
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    doy = cum_days[month] + day
    return doy

# Test
test_dates = [
    datetime(1992, 1, 1),
    datetime(1992, 2, 28),
    datetime(1992, 2, 29),
    datetime(1992, 3, 1),
    datetime(1992, 12, 31),
    datetime(1993, 2, 28),
    datetime(1993, 3, 1),
    datetime(1993, 12, 31),
]
for d in test_dates:
    print(f"{d} -> day {day_of_year(d)}")

# Check: 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, 31 Dec = 366
assert day_of_year(datetime(1992,1,1)) == 1
assert day_of_year(datetime(1992,2,28)) == 59
assert day_of_year(datetime(1992,2,29)) == 60
assert day_of_year(datetime(1992,3,1)) == 61
assert day_of_year(datetime(1992,12,31)) == 366
print("All assertions passed!")
