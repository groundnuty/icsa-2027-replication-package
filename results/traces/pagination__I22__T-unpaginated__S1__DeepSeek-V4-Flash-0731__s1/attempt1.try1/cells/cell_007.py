
import numpy as np
import datetime

def day_of_year(date):
    """Map a date to day of year 1-366 using the specified scheme."""
    y, m, d = date.year, date.month, date.day
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    # In leap years, Feb 29 = 60, and everything after is shifted by 1.
    # But wait, let me re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
    # This is NOT the standard day-of-year. In a non-leap year, 1 March would normally be day 60, but here it's day 61.
    # Wait, let me check: 1 Jan=1, so 31 Jan=31, 1 Feb=32, 28 Feb=59. Then 1 Mar=61 (skipping 60 in non-leap years).
    # In leap years, 29 Feb=60, 1 Mar=61.
    # So the mapping assigns 1-59 for Jan+Feb (up to Feb 28), then 60 for Feb 29 (leap years), then 61 for Mar 1 onwards.
    # Days after Feb: Mar 1 = 61 in both leap and non-leap years.
    # So Mar 31 = 61+30 = 91, Apr 1 = 92, etc.
    # Dec 31 = 366 in all years (since 31+28+31+... let me verify: 
    # Jan=31, Feb=28, Mar=31, Apr=30, May=31, Jun=30, Jul=31, Aug=31, Sep=30, Oct=31, Nov=30, Dec=31
    # Non-leap: 31+28+31+30+31+30+31+31+30+31+30+31 = 365
    # So Dec 31 should be day 366 per the spec.
    # In the mapping: 1 Jan=1, ..., 28 Feb=59, then 1 Mar=61, ..., 31 Dec=366.
    # This means the mapping for Mar 1 onwards is: standard_day_of_year + 1 (in non-leap years)
    # In leap years, 29 Feb=60, 1 Mar=61, so it's standard for Mar onwards.
    
    # Let me just compute it directly.
    # Day of year in standard sense:
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1  # adjust for Feb 29 in leap years
    
    # Now adjust to the specified scheme:
    # In non-leap years, standard doy for Mar 1 = 60, but spec says 61.
    # In leap years, standard doy for Mar 1 = 61, spec says 61.
    # So in non-leap years, add 1 for days after Feb 28.
    if not is_leap and m > 2:
        doy += 1
    
    return doy

# Test
print('2000 (leap):')
for d in [(2000,1,1),(2000,2,28),(2000,2,29),(2000,3,1),(2000,12,31)]:
    print(f'  {d}: {day_of_year(datetime.date(*d))}')
print('2001 (non-leap):')
for d in [(2001,1,1),(2001,2,28),(2001,3,1),(2001,12,31)]:
    print(f'  {d}: {day_of_year(datetime.date(*d))}')
print('1992 (leap):')
for d in [(1992,1,1),(1992,2,28),(1992,2,29),(1992,3,1),(1992,12,31)]:
    print(f'  {d}: {day_of_year(datetime.date(*d))}')
