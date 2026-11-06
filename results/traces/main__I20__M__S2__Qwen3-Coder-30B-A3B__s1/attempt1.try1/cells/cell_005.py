import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60
    else:
        # Get day of year (1-366)
        return int(dt.strftime('%j'))

def doy_to_date(doy):
    """Convert day of year to date string"""
    # Create a date for Jan 1 of a non-leap year
    jan1 = datetime(2001, 1, 1)
    # Add doy-1 days to get the date
    target_date = jan1 + timedelta(days=doy-1)
    return target_date.strftime('%Y-%m-%d')

# Test the function
print("Testing date conversion:")
test_dates = ['2012-01-01', '2012-02-28', '2012-02-29', '2012-03-01', '2012-12-31']
for date in test_dates:
    doy = date_to_doy(date)
    print(f"{date} -> DOY {doy}")