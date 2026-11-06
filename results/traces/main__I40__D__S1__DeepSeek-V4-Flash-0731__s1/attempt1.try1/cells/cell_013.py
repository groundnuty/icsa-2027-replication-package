
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Day of year mapping as specified
# 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
# Non-leap years have no day 60

def date_to_doy(year, month, day):
    """Map a date to day of year 1-366 as specified."""
    # For non-leap years, Feb 28 = 59, Mar 1 = 61
    # For leap years, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61
    # So: Jan has 31 days, Feb has 29 days (always counting Feb 29 as day 60 even in non-leap years)
    # Actually the mapping says: 28 Feb = 59, 29 Feb = 60, 1 Mar = 61
    # So it always counts as if there's a Feb 29
    # Jan: 1-31
    # Feb: 32-59 (28 days) or 32-60 (29 days)
    # Let me check: 1 Jan = 1, so Jan has days 1-31
    # Feb 1 = 32, Feb 28 = 59 (31+28), Feb 29 = 60, Mar 1 = 61
    # So the mapping is: always treat Feb as having 29 days, i.e., day 60 = Feb 29
    # For non-leap years, there's no Feb 29, so no date maps to 60
    
    # Check if it's a leap year
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    # Days before each month (treating Feb as always 29 days for the mapping)
    # This is the key: the mapping says Feb 28 = 59 and Mar 1 = 61
    # So there's a gap at day 60 (Feb 29)
    # Jan: days 1-31
    # Feb: days 32-59 (or 32-60 in leap years)
    # Mar: days 61+
    
    month_start = {
        1: 1,
        2: 32,
        3: 61,
        4: 92,
        5: 122,
        6: 153,
        7: 183,
        8: 214,
        9: 245,
        10: 275,
        11: 306,
        12: 336
    }
    
    # Feb has 29 days in the mapping (28 Feb = 59, so Feb has 28 days + 29th = 60)
    # Wait, Jan has 31 days (1-31), so Feb 1 = 32
    # Feb 28 = 32+27 = 59. Feb 29 = 60. So Feb has 29 days.
    # Mar 1 = 61. So days 1-31 = Jan, 32-59 = Feb (28 days), 60 = Feb 29, 61-91 = Mar (31 days)
    
    days_in_month = {
        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }
    
    doy = sum(days_in_month[m] for m in range(1, month)) + day
    return doy

# Test the mapping
test_cases = [
    (2024, 1, 1),   # Leap year, Jan 1 = 1
    (2024, 2, 28),  # Leap year, Feb 28 = 59
    (2024, 2, 29),  # Leap year, Feb 29 = 60
    (2024, 3, 1),   # Leap year, Mar 1 = 61
    (2024, 12, 31), # Leap year, Dec 31 = 366
    (2023, 1, 1),   # Non-leap year, Jan 1 = 1
    (2023, 2, 28),  # Non-leap year, Feb 28 = 59
    (2023, 3, 1),   # Non-leap year, Mar 1 = 61
    (2023, 12, 31), # Non-leap year, Dec 31 = 366
]

for tc in test_cases:
    print(f"{tc[0]}-{tc[1]:02d}-{tc[2]:02d} -> doy {date_to_doy(*tc)}")

# Let me verify: 1 Mar should be 61 in both leap and non-leap years
# Jan 31 + Feb 28 = 59, so Mar 1 = 60 in the regular calendar
# But the spec says Feb 28 = 59 and Mar 1 = 61
# So the mapping inserts an extra day (Feb 29 = 60) regardless of leap year
# This means: days 1-31 = Jan, 32-59 = Feb 1-28, 60 = Feb 29 (only in leap years), 61 = Mar 1

# Let me verify: in a non-leap year, Mar 1 = 61. Jan has 31 days, Feb has 28 days. 31+28 = 59. So Mar 1 = 60 in a regular count.
# But spec says Mar 1 = 61. So there's an implicit Feb 29 that adds 1 to all days after Feb 28.
# So in a non-leap year, days 60 through 366 are shifted by 1 compared to the actual day of year.
# Actually wait - the spec says "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366"
# This is just saying: Jan 1 = day 1, and the months have their usual day counts, but with Feb 29 always counted as day 60.
# So days: Jan 1-31 = 1-31, Feb 1-29 = 32-60, Mar 1-31 = 61-91, etc.
# But in non-leap years, there's no Feb 29, so day 60 doesn't exist.
# So the mapping treats every year as having a Feb 29 slot, but non-leap years just don't have data for day 60.

# Check: 28 Feb = 59 means Jan (31) + Feb 28 = 59. Correct.
# Feb 29 = 60. Mar 1 = 61. Correct.
# Dec 31 = 366. Let's check: Jan 31 + Feb 29 + Mar 31 + Apr 30 + May 31 + Jun 30 + Jul 31 + Aug 31 + Sep 30 + Oct 31 + Nov 30 + Dec 31
# = 31+29+31+30+31+30+31+31+30+31+30+31 = 366. Correct.

# So the doy function is correct. The month_start mapping should be:
# Jan 1 = 1
# Feb 1 = 32
# Mar 1 = 61
# Apr 1 = 92
# May 1 = 122
# Jun 1 = 153
# Jul 1 = 183
# Aug 1 = 214
# Sep 1 = 245
# Oct 1 = 275
# Nov 1 = 306
# Dec 1 = 336

# Let me verify Dec 31 = 336 + 31 - 1 = 366. Correct.
