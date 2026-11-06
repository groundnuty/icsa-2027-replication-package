
import numpy as np
import pandas as pd

def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

# Test cases
test_cases = [
    ('1992-01-01', 1),   # Jan 1 = 1
    ('1992-02-28', 59),  # Feb 28 = 59
    ('1992-02-29', 60),  # Feb 29 = 60 (leap year)
    ('1992-03-01', 61),  # Mar 1 = 61
    ('1993-02-28', 59),  # Feb 28 = 59 (non-leap)
    ('1993-03-01', 61),  # Mar 1 = 61 (non-leap, day 60 skipped)
    ('1992-12-31', 366), # Dec 31 = 366
    ('1993-12-31', 366), # Dec 31 = 366 (non-leap, +1 for Mar+)
    ('2017-06-01', 153), # Jun 1 = 153 (non-leap)
    ('2017-08-31', 244), # Aug 31 = 244 (non-leap)
]

for date_str, expected in test_cases:
    t = np.datetime64(date_str)
    result = doy_from_datetime64(t)
    status = "PASS" if result == expected else "FAIL"
    print(f"{date_str}: DOY={result}, expected={expected} [{status}]")
