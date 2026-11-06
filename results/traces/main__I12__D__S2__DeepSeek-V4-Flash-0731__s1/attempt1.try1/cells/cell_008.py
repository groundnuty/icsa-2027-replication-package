
import numpy as np
import pandas as pd

def date_to_doy(dt):
    """Map date to day of year 1-366 using fixed calendar.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    month = dt.month
    day = dt.day
    # Cumulative days before each month in the "366-day" scheme
    # Jan=1, Feb=32, Mar=61, Apr=92, May=122, Jun=153, Jul=183, Aug=214, Sep=245, Oct=275, Nov=306, Dec=336
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return days_before[month-1] + day

# Verify
test_dates = [
    pd.Timestamp('2000-01-01'),  # should be 1
    pd.Timestamp('2000-02-28'),  # should be 59
    pd.Timestamp('2000-02-29'),  # should be 60
    pd.Timestamp('2000-03-01'),  # should be 61
    pd.Timestamp('2000-12-31'),  # should be 366
]
for d in test_dates:
    print(d.date(), "->", date_to_doy(d))

# Check non-leap: 2001-03-01 should also be 61
print(pd.Timestamp('2001-03-01').date(), "->", date_to_doy(pd.Timestamp('2001-03-01')))
# And 2001-02-28 = 59
print(pd.Timestamp('2001-02-28').date(), "->", date_to_doy(pd.Timestamp('2001-02-28')))
# 2001-12-31 = 365
print(pd.Timestamp('2001-12-31').date(), "->", date_to_doy(pd.Timestamp('2001-12-31')))
