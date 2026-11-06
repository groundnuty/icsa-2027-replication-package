
import numpy as np
import pandas as pd

# Generate all dates from 1982-01-01 to 2023-12-31
all_dates = pd.date_range('1982-01-01', '2023-12-31', freq='D')

# Check the day-of-year mapping matches what we need
# 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366

def fixed_doy(date):
    """Map a date to day-of-year 1-366 using the fixed convention."""
    month = date.month
    day = date.day
    # Days before the month
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # But Feb is special: 28 Feb = 59, 29 Feb = 60
    # In the fixed convention, day 60 is Feb 29, day 61 is Mar 1
    # So we use Feb=28 days always for the cumulative offset
    # But actually, the convention says: 1 Jan=1, ..., 28 Feb=59, 29 Feb=60, 1 Mar=61
    # In non-leap years there's no Feb 29, so no day 60
    # 1 Mar is always 61, so we need Feb to count as 28 days before March
    # But 28 Feb = 59 means Jan(31) + 28 = 59. Correct.
    # And 1 Mar = 61 = 59 + 2 = 31 + 28 + 2... wait, that's Jan(31) + Feb(28) + 1 = 60.
    # Hmm, 1 Mar should be 61. Let me recount: 1 Jan=1, 31 Jan=31, 1 Feb=32, 28 Feb=59, 1 Mar=60??
    # No wait: 31 + 28 = 59, so 1 Mar = 60. But the spec says 1 Mar = 61.
    # Let me re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
    # So 31 Jan = 31, 1 Feb = 32, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
    # This means Jan has 31 days (days 1-31), and then Feb has 28 days in the count 
    # (days 32-59) even in leap years when there IS a Feb 29 (day 60).
    # So in the fixed mapping: Feb is always counted as having 28 days (days 32-59),
    # and Feb 29 is assigned day 60 as a special case.
    # Then Mar 1 = 61 = 31 + 28 + 2 = 61. Hmm, 31 (Jan) + 28 (Feb) = 59, so Mar 1 = 60.
    # But spec says Mar 1 = 61. So there's an offset.
    # Let me recount: 1 Jan = 1. 31 Jan = 31. 1 Feb = 32. 
    # If Feb has 28 days in the fixed counting: 28 Feb = 59, 1 Mar = 60.
    # But spec says 1 Mar = 61. So the spec must be counting Feb as having 29 days in the mapping:
    # 1 Feb = 32, ..., 29 Feb = 60, 1 Mar = 61.
    # And 28 Feb = 59. That's consistent: 32 + 27 = 59 (Feb 28 is 28th of Feb, so day 32+27=59).
    # Wait, 1 Feb = 32, 2 Feb = 33, ..., 28 Feb = 32+27 = 59. Yes.
    # 29 Feb = 60, 1 Mar = 61. So Feb is counted as 29 days in the fixed mapping.
    # In non-leap years, there's no Feb 29 (no day 60), and Feb has 28 days.
    # But day 61 is still Mar 1. So in non-leap years, Mar 1 = 61 still holds.
    # The fixed mapping always counts Feb as having 29 days worth of slots:
    # Feb 1-28 = days 32-59, Feb 29 = day 60, Mar 1 = day 61.
    # So for non-leap years, day 60 is simply unused.
    
    # Cumulative days by month using Feb=29 days for the purpose of fixed doy mapping
    cum = [0, 31, 31+29, 31+29+31, 31+29+31+30, 31+29+31+30+31,
           31+29+31+30+31+30, 31+29+31+30+31+30+31,
           31+29+31+30+31+30+31+31, 31+29+31+30+31+30+31+31+30,
           31+29+31+30+31+30+31+31+30+31,
           31+29+31+30+31+30+31+31+30+31+30]
    # cum[month-1] gives the number of days before this month
    return cum[month-1] + day

# Verify
print("1 Jan:", fixed_doy(pd.Timestamp('2020-01-01')))
print("28 Feb:", fixed_doy(pd.Timestamp('2020-02-28')))
print("29 Feb:", fixed_doy(pd.Timestamp('2020-02-29')))
print("1 Mar:", fixed_doy(pd.Timestamp('2020-03-01')))
print("31 Dec:", fixed_doy(pd.Timestamp('2020-12-31')))
print("28 Feb (non-leap):", fixed_doy(pd.Timestamp('2019-02-28')))
print("1 Mar (non-leap):", fixed_doy(pd.Timestamp('2019-03-01')))
