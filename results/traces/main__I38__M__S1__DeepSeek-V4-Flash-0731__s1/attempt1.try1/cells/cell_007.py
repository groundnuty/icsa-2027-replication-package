
from datetime import date, timedelta

def day_of_year(d):
    """Map date to day-of-year 1-366 (Feb always has 29 days in this mapping)."""
    # Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, ..., Dec 31 = 366
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:d.month]) + d.day
    return doy

# Test
print(day_of_year(date(2000, 1, 1)))   # 1
print(day_of_year(date(2000, 2, 28)))  # 59
print(day_of_year(date(2000, 2, 29)))  # 60
print(day_of_year(date(2000, 3, 1)))   # 61
print(day_of_year(date(2000, 12, 31))) # 366
print(day_of_year(date(2003, 1, 1)))   # 1
print(day_of_year(date(2003, 2, 28)))  # 59
print(day_of_year(date(2003, 3, 1)))   # 61
print(day_of_year(date(2003, 12, 31))) # 366
print(day_of_year(date(2003, 6, 1)))   # Should be: 31+29+31+30+31+1 = 153
print(day_of_year(date(2003, 6, 15)))  # 167
print(day_of_year(date(2003, 8, 31)))  # 31+29+31+30+31+30+31+31 = 244
