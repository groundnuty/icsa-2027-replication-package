import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    doy = int(dt.strftime('%j'))
    # Special handling for Feb 29th (day 60)
    if dt.month == 2 and dt.day == 29:
        return 60
    return doy

def doy_to_date(doy):
    """Convert day-of-year to date string (assuming non-leap year)"""
    if doy == 60:
        return "02-29"
    base_date = datetime(2001, 1, 1)  # Non-leap year
    target_date = base_date + timedelta(days=doy-1)
    return target_date.strftime("%m-%d")

# Test the function
test_dates = ['1992-01-01', '1992-02-28', '1992-02-29', '1992-03-01', '2002-12-31']
for date in test_dates:
    print(f"{date} -> DOY: {date_to_doy(date)}")