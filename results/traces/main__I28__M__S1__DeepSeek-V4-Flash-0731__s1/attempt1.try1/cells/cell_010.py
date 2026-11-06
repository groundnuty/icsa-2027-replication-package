
from datetime import date, timedelta

def doy_of_date(d):
    """Compute day of year (1-366) using the fixed mapping (Feb always has 29 days)."""
    # Jan: 1-31
    # Feb: 32-59 (Feb 28), Feb 29 = 60 in leap years
    # Mar onwards: use Feb = 29 days
    month = d.month
    day = d.day
    days_in_months_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # For a normal year: Jan=31, Feb=28, Mar=31, Apr=30, May=31, Jun=30, Jul=31, Aug=31, Sep=30, Oct=31, Nov=30, Dec=31
    # But we treat Feb as 29, so:
    # Jan=31, Feb=29, Mar=31, Apr=30, May=31, Jun=30, Jul=31, Aug=31, Sep=30, Oct=31, Nov=30, Dec=31
    # cumulative: Jan=0, Feb=31, Mar=60, Apr=91, May=121, Jun=152, Jul=182, Aug=213, Sep=244, Oct=274, Nov=305, Dec=335
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Verify
print("Jan 1:", doy_of_date(date(1992, 1, 1)))  # Should be 1
print("Feb 28:", doy_of_date(date(1992, 2, 28)))  # Should be 59
print("Feb 29:", doy_of_date(date(1992, 2, 29)))  # Should be 60
print("Mar 1:", doy_of_date(date(1992, 3, 1)))  # Should be 61
print("Dec 31:", doy_of_date(date(1992, 12, 31)))  # Should be 366
print("Mar 1 non-leap:", doy_of_date(date(1993, 3, 1)))  # Should be 61
print("Dec 31 non-leap:", doy_of_date(date(1993, 12, 31)))  # Should be 366
print("Jun 1:", doy_of_date(date(2013, 6, 1)))  # Should be 153
print("Aug 31:", doy_of_date(date(2013, 8, 31)))  # Should be 244
