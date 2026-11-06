
import numpy as np
import pandas as pd

# Day of year mapping: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366
# Non-leap years have no day 60

def doy_from_date(dt):
    """Get day of year from 1-366 where non-leap years have no day 60."""
    dt = pd.Timestamp(dt)
    year = dt.year
    month = dt.month
    day = dt.day
    
    # Check if leap year
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    # Days in months before this one
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    days_before = sum(month_days[:month-1])
    
    if month > 2 and is_leap:
        days_before += 1
    
    doy = days_before + day
    
    if is_leap and month == 2 and day == 29:
        doy = 60
    elif not is_leap and month >= 3:
        # Non-leap year: shift by 1 after Feb 28
        # Actually wait, let me reconsider
        pass
    
    return doy

# Let me verify the mapping from the task description:
# 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366
# Non-leap years have no day 60

# This means for non-leap years:
# Jan 1 = 1, ..., Jan 31 = 31
# Feb 1 = 32, ..., Feb 28 = 59
# Mar 1 = 60 (not 61!), but the spec says 1 March = 61

# Wait, let me re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
# So for leap years, 29 Feb = 60 and 1 Mar = 61
# For non-leap years, there is no day 60. So 1 Mar = ... hmm
# If non-leap years have no day 60, then:
#   Feb 28 = 59, and then 1 Mar = 60? No wait...
# The spec says "Non-leap years have no day 60". So the mapping is:
# For non-leap: 1 Mar = 60? No, because the spec says 1 Mar = 61.
# Hmm, I think the mapping is: for non-leap years, 1 Mar also = 61 (just like leap years), but day 60 doesn't exist in non-leap years.
# Actually that can't be right either because then the count would be wrong.

# Let me reconsider. The mapping from the task:
# 1 Jan = 1
# 28 Feb = 59
# 29 Feb = 60
# 1 Mar = 61
# ...
# 31 Dec = 366

# So the DOY is based on the leap-year calendar. For non-leap years, day 60 simply doesn't occur.
# So for non-leap years: 1 Jan = 1, ..., 28 Feb = 59, then 1 Mar = 61 (skipping 60).
# Wait, that means for non-leap years, Mar 1 = 61 but Feb 28 = 59, so days 60 is skipped entirely.

# Actually, I think the mapping is simpler: it's just the "calendar day of year" in a leap year.
# So we use the leap-year day numbering for all years. In non-leap years, there's no day 60.
# This means: in non-leap years, Feb 28 = 59, Mar 1 = 61 (because day 60 would be Feb 29 which doesn't exist).

# Let me verify: 31 Dec = 366 in all years? For a leap year, Dec 31 has 366 days elapsed from Jan 1 (inclusive). 
# Jan 31 days, Feb 29, Mar 31, Apr 30, May 31, Jun 30, Jul 31, Aug 31, Sep 30, Oct 31, Nov 30 = 31+29+31+30+31+30+31+31+30+31+30 = 335, plus 31 for Dec = 366. Yes.
# For non-leap: 31+28+31+30+31+30+31+31+30+31+30+31 = 365. So Dec 31 would be 365 in the normal numbering.
# But the spec says 31 Dec = 366. So they're using leap-year numbering for all years.

# So the DOY function is: use the leap-year month lengths.
# In non-leap years, there's no day 60 because Feb 29 doesn't exist.

def doy(date):
    """Map a date to day of year 1-366 using leap-year numbering."""
    dt = pd.Timestamp(date)
    month = dt.month
    day = dt.day
    
    # Leap-year month lengths
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_lengths[:month-1]) + day
    return doy

# Verify
test_cases = [
    ('1992-01-01', 1),
    ('1992-02-28', 59),
    ('1992-02-29', 60),
    ('1992-03-01', 61),
    ('1992-12-31', 366),
    ('1993-01-01', 1),
    ('1993-02-28', 59),
    ('1993-03-01', 61),  # no day 60 in non-leap
    ('1993-12-31', 366),
    ('2000-02-29', 60),
    ('2001-02-28', 59),
    ('2001-03-01', 61),
]

for date_str, expected in test_cases:
    result = doy(date_str)
    status = "OK" if result == expected else f"FAIL (got {result})"
    print(f"{date_str} -> DOY {result}, expected {expected}: {status}")
