
import numpy as np
from datetime import date, timedelta

def day_of_year(y, m, d):
    """Map a date to day of year 1-366 as per the task spec."""
    # Days in each month for non-leap year
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check if leap year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    
    if is_leap:
        days_in_month[1] = 29
    
    doy = sum(days_in_month[:m-1]) + d
    return doy

# Verify
print(f"1 Jan 2000: {day_of_year(2000, 1, 1)}")  # Should be 1
print(f"28 Feb 2000: {day_of_year(2000, 2, 28)}")  # Should be 59
print(f"29 Feb 2000: {day_of_year(2000, 2, 29)}")  # Should be 60
print(f"1 Mar 2000: {day_of_year(2000, 3, 1)}")  # Should be 61
print(f"31 Dec 2000: {day_of_year(2000, 12, 31)}")  # Should be 366
print(f"28 Feb 2001: {day_of_year(2001, 2, 28)}")  # Should be 59
print(f"1 Mar 2001: {day_of_year(2001, 3, 1)}")  # Should be 61
print(f"31 Dec 2001: {day_of_year(2001, 12, 31)}")  # Should be 365

# So for non-leap year: Mar 1 should be 61, not 60
# My function gives Mar 1 2001 = 60, which is wrong
# The correct mapping: for non-leap years, after Feb 28 (59), the next day is Mar 1 = 61

# Let me redo this: the day-of-year mapping is based on month and day, where
# the mapping for Mar 1 and after is the same regardless of leap year
# For Jan and Feb: day 1-59 same in all years
# For Mar onwards: same mapping in all years

def day_of_year_fixed(y, m, d):
    """Map a date to day of year 1-366 as per the task spec."""
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m >= 3:
        # For Mar onwards, the mapping is the same in all years
        # Mar: 61-91, Apr: 92-122, May: 123-153, Jun: 154-183, Jul: 184-214, Aug: 215-245, Sep: 246-275, Oct: 276-306, Nov: 307-336, Dec: 337-366
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

# Verify
print("\nWith fixed function:")
print(f"1 Jan 2000: {day_of_year_fixed(2000, 1, 1)}")
print(f"28 Feb 2000: {day_of_year_fixed(2000, 2, 28)}")
print(f"29 Feb 2000: {day_of_year_fixed(2000, 2, 29)}")
print(f"1 Mar 2000: {day_of_year_fixed(2000, 3, 1)}")
print(f"31 Dec 2000: {day_of_year_fixed(2000, 12, 31)}")
print(f"28 Feb 2001: {day_of_year_fixed(2001, 2, 28)}")
print(f"1 Mar 2001: {day_of_year_fixed(2001, 3, 1)}")
print(f"31 Dec 2001: {day_of_year_fixed(2001, 12, 31)}")

# Check: does Mar 1 always = 61?
# In a leap year: Jan=1-31, Feb=32-60, so Mar 1 = 61 ✓
# In a non-leap year: Jan=1-31, Feb=32-59, then Mar 1 = 61 ✓ (skipping 60)
