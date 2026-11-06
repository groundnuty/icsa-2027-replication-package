
from datetime import date

def day_of_year_366(d):
    """Map a date to day of year 1-366.
    Always treats Feb as having 29 days.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60 (no Feb 29 date exists).
    """
    m, day = d.month, d.day
    # Days in each month, always using Feb = 29
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:m-1]) + day
    return doy

print(day_of_year_366(date(2021, 1, 1)))  # 1
print(day_of_year_366(date(2021, 2, 28)))  # 59
print(day_of_year_366(date(2020, 2, 29)))  # 60
print(day_of_year_366(date(2021, 3, 1)))   # 61
print(day_of_year_366(date(2021, 12, 31))) # 366
print(day_of_year_366(date(2021, 6, 1)))   # should be 31+29+31+30+31+1 = 153
print(day_of_year_366(date(2021, 8, 31)))  # should be 31+29+31+30+31+30+31+31 = 244
