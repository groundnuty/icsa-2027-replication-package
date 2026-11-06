
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Day of year mapping (1-366)
def day_of_year_366(d):
    """Map a date to day of year 1-366, where 29 Feb = 60."""
    m, day = d.month, d.day
    # Days in each month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # For leap years, Feb has 29 days
    if d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0):
        days_in_month[1] = 29
    
    doy = sum(days_in_month[:m-1]) + day
    return doy

# Test
print(day_of_year_366(date(2021, 1, 1)))  # should be 1
print(day_of_year_366(date(2021, 2, 28)))  # should be 59
print(day_of_year_366(date(2020, 2, 29)))  # should be 60 (leap year)
print(day_of_year_366(date(2021, 3, 1)))   # should be 61
print(day_of_year_366(date(2021, 12, 31))) # should be 366

# Verify with 2021 (non-leap): Mar 1 should be 60
# 31 + 28 = 59 for Feb 28, so Mar 1 = 60
print(day_of_year_366(date(2021, 3, 1)))  # should be 60 in non-leap? 
# Wait, let me re-read the task: "1 March = 61"
# So in non-leap years, Mar 1 = 61? Let me re-read.
# "Map every date to a day of year from 1 to 366 by month and day: 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
# So the mapping is: 28 Feb = 59, 29 Feb = 60 (in leap years), 1 Mar = 61
# But in non-leap years, there's no Feb 29. So what is 1 Mar in a non-leap year?
# The task says "Non-leap years have no day 60."
# So in non-leap years: Jan = 1-31, Feb = 32-59 (Feb 28 = 59), Mar 1 = 60? 
# No wait, it says "1 March = 61". So Mar 1 always = 61 regardless of leap year.
# Let me re-read: "Map every date to a day of year from 1 to 366 by month and day: 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
# So the mapping is: Jan 1 = 1, ..., Jan 31 = 31, Feb 1 = 32, ..., Feb 28 = 59, Feb 29 = 60 (leap years only), Mar 1 = 61, ...
# In non-leap years, Feb 28 = 59, and Mar 1 = 60? 
# No! The task explicitly says "1 March = 61". So Mar 1 is ALWAYS day 61.
# In non-leap years, day 60 just doesn't exist as a date.
# So the mapping is by month and day, not by counting days from Jan 1.
# Jan 1 = 1, Jan 2 = 2, ..., Jan 31 = 31
# Feb 1 = 32, Feb 2 = 33, ..., Feb 28 = 59
# Feb 29 = 60 (only in leap years)
# Mar 1 = 61, Mar 2 = 62, ...
# Dec 31 = 366

# So the day-of-year is: sum of days in months before + day, BUT with Feb 29 inserted.
# In a non-leap year, after Feb 28 (=59), Mar 1 would be 60.
# But the task says Mar 1 = 61. So we always add an extra day at Feb 29.
# In other words: 
# if month <= 2: doy = (month-1)*31 + day... no that's wrong.
# Let me think of it as: for any date, the day of year is computed as if it's a leap year.
# For non-leap years: Jan 31 = 31, Feb 28 = 59 (31+28), Mar 1 = 61 (31+28+2 = 61? No...)

# Hmm, let me reconsider. In the standard Gregorian calendar with Feb 29:
# Jan 31 = 31
# Feb 28 = 59
# Feb 29 = 60
# Mar 1 = 61
# ...
# Dec 31 = 366

# This is the standard "day of year including leap day" mapping.
# For non-leap years: Jan 1 = 1, ..., Feb 28 = 59, Mar 1 = 60 (in standard), but the task says Mar 1 = 61.
# So in non-leap years, Mar 1 is still 61. That means day 60 is skipped in non-leap years.
# It's like we always count as if it's a leap year for the mapping.

# So the mapping is: for any date, compute doy as:
# doy = sum(days_in_month[:m-1]) + day, where days_in_month includes Feb = 29 always.
# So days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
# This gives: Jan 1 = 1, ..., Jan 31 = 31, Feb 1 = 32, ..., Feb 28 = 59, 
# Mar 1 = 60+1 = 61? Let me compute: 31 + 29 = 60 for end of Feb, so Mar 1 = 61. ✓
# Feb 29 = 60 ✓
# Dec 31 = 31+29+31+30+31+30+31+31+30+31+30+31 = 366 ✓

# So yes, the mapping always treats Feb as having 29 days.
print("Re-verify:")
print(day_of_year_366(date(2021, 1, 1)))  # 1
print(day_of_year_366(date(2021, 2, 28)))  # 59
print(day_of_year_366(date(2021, 3, 1)))   # 61
print(day_of_year_366(date(2020, 2, 29)))  # 60
print(day_of_year_366(date(2021, 12, 31))) # 366
