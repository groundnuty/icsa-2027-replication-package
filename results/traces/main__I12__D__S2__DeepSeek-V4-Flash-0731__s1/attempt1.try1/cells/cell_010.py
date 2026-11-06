
import pandas as pd

def date_to_doy(dt):
    """Map date to day of year 1-366 using fixed calendar.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    month = dt.month
    day = dt.day
    # Cumulative days before each month in the 366-day scheme
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Verify
test_dates = [
    pd.Timestamp('2000-01-01'),  # should be 1
    pd.Timestamp('2000-02-28'),  # should be 59
    pd.Timestamp('2000-02-29'),  # should be 60
    pd.Timestamp('2000-03-01'),  # should be 61
    pd.Timestamp('2000-12-31'),  # should be 366
    pd.Timestamp('2000-02-01'),  # should be 32
    pd.Timestamp('2000-04-01'),  # should be 92
]
for d in test_dates:
    print(d.date(), "->", date_to_doy(d))

# Check non-leap year
print(pd.Timestamp('2001-03-01').date(), "->", date_to_doy(pd.Timestamp('2001-03-01')))
print(pd.Timestamp('2001-12-31').date(), "->", date_to_doy(pd.Timestamp('2001-12-31')))
