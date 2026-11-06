
def day_of_year(dt):
    """Map a date to day of year 1-366 by month and day.
    1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366.
    This is a fixed mapping (leap-year calendar), regardless of actual year.
    """
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Test
from datetime import date
print('Jan 1:', day_of_year(date(1992, 1, 1)))
print('Feb 28:', day_of_year(date(1992, 2, 28)))
print('Feb 29:', day_of_year(date(1992, 2, 29)))
print('Mar 1:', day_of_year(date(1992, 3, 1)))
print('Dec 31:', day_of_year(date(1992, 12, 31)))
print('Dec 30:', day_of_year(date(1992, 12, 30)))

# In a non-leap year
print('Mar 1 non-leap:', day_of_year(date(1993, 3, 1)))
print('Feb 28 non-leap:', day_of_year(date(1993, 2, 28)))
