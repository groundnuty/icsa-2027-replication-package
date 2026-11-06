
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Define the day-of-year mapping (1-366 by month/day, leap-year style)
def day_of_year(year, month, day):
    """Map date to day of year 1-366 assuming leap year style."""
    # Days before each month (leap year)
    month_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return month_days[month-1] + day

# Test
print(day_of_year(2000, 1, 1))  # 1
print(day_of_year(2000, 2, 28))  # 59
print(day_of_year(2000, 2, 29))  # 60
print(day_of_year(2000, 3, 1))   # 61
print(day_of_year(2000, 12, 31)) # 366
print(day_of_year(2001, 3, 1))   # 61 (non-leap year but same mapping)
print(day_of_year(2001, 12, 31)) # 366
# Check Feb 28 in non-leap year
print(day_of_year(2001, 2, 28))  # 59
