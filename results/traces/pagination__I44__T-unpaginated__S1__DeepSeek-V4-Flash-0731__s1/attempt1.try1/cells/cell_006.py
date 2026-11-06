from datetime import date, timedelta
import calendar

def doy_from_date(d):
    """Map a date to day of year 1-366."""
    return d.timetuple().tm_yday

# Check mapping: Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, Dec 31 = 366
print(doy_from_date(date(1992, 1, 1)))  # 1
print(doy_from_date(date(1992, 2, 28)))  # 59
print(doy_from_date(date(1992, 2, 29)))  # 60
print(doy_from_date(date(1992, 3, 1)))   # 61
print(doy_from_date(date(1992, 12, 31))) # 366
print(doy_from_date(date(1991, 12, 31))) # 365 (non-leap)
print(doy_from_date(date(1993, 2, 28)))  # 59 (non-leap year)
print(doy_from_date(date(1993, 3, 1)))   # 60 (non-leap, since Feb has 28 days)

# Let me verify: in a non-leap year, March 1 is day 60
print(doy_from_date(date(1993, 12, 31)))  # 365

# In a leap year, Dec 31 is 366
print(doy_from_date(date(1992, 12, 31)))  # 366
