import numpy as np
from datetime import datetime, timedelta

# Day-of-year mapping
def day_of_year(dt):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:dt.month-1]) + dt.day

# Test the mapping
test_dates = [
    datetime(1992, 1, 1), datetime(1992, 2, 28), datetime(1992, 2, 29),
    datetime(1992, 3, 1), datetime(1992, 12, 31),
    datetime(1993, 1, 1), datetime(1993, 2, 28), datetime(1993, 3, 1),
    datetime(1993, 12, 31),
    datetime(2000, 2, 29), datetime(2000, 12, 31)
]
for dt in test_dates:
    print(f"{dt.date()} -> DOY {day_of_year(dt)}")
