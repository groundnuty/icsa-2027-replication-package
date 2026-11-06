
import numpy as np
import datetime as dt

def day_of_year(ts):
    """Compute custom day of year: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366.
    Non-leap years have no day 60.
    """
    d = dt.datetime.fromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9, tz=dt.timezone.utc)
    year = d.year
    month = d.month
    day = d.day
    
    # Standard day of year
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    
    std_doy = sum(days_in_month[:month-1]) + day
    
    # If non-leap year and date is after Feb 28, add 1
    if not is_leap and month > 2:
        std_doy += 1
    
    return std_doy

# Test
test_dates = [
    np.datetime64('1992-01-01'),  # leap
    np.datetime64('1992-02-28'),  # leap
    np.datetime64('1992-02-29'),  # leap
    np.datetime64('1992-03-01'),  # leap
    np.datetime64('1992-12-31'),  # leap
    np.datetime64('1993-01-01'),  # non-leap
    np.datetime64('1993-02-28'),  # non-leap
    np.datetime64('1993-03-01'),  # non-leap
    np.datetime64('1993-12-31'),  # non-leap
    np.datetime64('1996-02-29'),  # leap
    np.datetime64('2000-02-29'),  # leap
    np.datetime64('2000-12-31'),  # leap
]
for t in test_dates:
    print(t, "->", day_of_year(t))
