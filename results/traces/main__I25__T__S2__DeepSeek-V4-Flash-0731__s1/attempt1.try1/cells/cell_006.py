
import numpy as np
from datetime import datetime, timedelta

def day_of_year(dt):
    """Map a date to day of year 1-366 based on month and day."""
    month = dt.month
    day = dt.day
    # Cumulative days before each month (for non-leap year, but we add Feb 29 as day 60)
    cum_days = [0, 31, 59, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    # This assumes: Jan=1..31, Feb=32..59/60, Mar=61..91, Apr=92..121, May=122..152,
    # Jun=153..182, Jul=183..213, Aug=214..244, Sep=245..274, Oct=275..305, Nov=306..335, Dec=336..366
    
    # Let me verify: 
    # Jan 1 = cum_days[0] + 1 = 1 ✓
    # Feb 1 = cum_days[1] + 1 = 32 ✓
    # Feb 28 = cum_days[1] + 28 = 59 ✓
    # Feb 29 = cum_days[1] + 29 = 60 ✓
    # Mar 1 = cum_days[2] + 1 = 60? No, cum_days[2] = 59, so 59+1 = 60. But we want 61.
    
    # Hmm, let me recalculate.
    # cum_days should be: [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # Wait no. Let me think again.
    
    # For a non-leap year, days in each month: 31,28,31,30,31,30,31,31,30,31,30,31
    # Cumulative: 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334
    
    # But the task says Feb 29 = 60, Mar 1 = 61.
    # So in a "leap year convention": 
    # Jan = 1-31, Feb = 32-60 (including 29th = 60), Mar = 61-91, ...
    # Cumulative: 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335
    
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    
    # But for non-leap years, Feb only has 28 days, so Feb 28 = 59 and Mar 1 = 61.
    # The mapping by month and day is: month m, day d -> cum_days[m-1] + d
    # where cum_days is the leap-year cumulative (since day 60 = Feb 29).
    
    # So for any date, doy = cum_days_leap[month-1] + day
    # Jan 1 = 0 + 1 = 1 ✓
    # Feb 28 = 31 + 28 = 59 ✓
    # Feb 29 = 31 + 29 = 60 ✓
    # Mar 1 = 60 + 1 = 61 ✓
    # Dec 31 = 335 + 31 = 366 ✓
    
    return cum_days_leap[month - 1] + day

# Test
test_dates = [
    datetime(1992, 1, 1),
    datetime(1992, 2, 28),
    datetime(1992, 2, 29),
    datetime(1992, 3, 1),
    datetime(1993, 3, 1),  # non-leap year
    datetime(1992, 12, 31),
    datetime(1992, 6, 1),
    datetime(1992, 8, 31),
]
for dt in test_dates:
    print(f"{dt.strftime('%Y-%m-%d')}: doy={day_of_year(dt)}")
