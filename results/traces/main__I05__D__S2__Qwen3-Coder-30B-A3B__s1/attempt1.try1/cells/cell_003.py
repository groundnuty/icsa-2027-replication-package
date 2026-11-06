import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60
    else:
        # Get day of year, adjusting for leap year
        doy = dt.timetuple().tm_yday
        # Adjust for leap year - if it's after Feb 28 and we're not in a leap year, subtract 1
        if dt.month > 2:
            # Check if this year is a leap year
            year = dt.year
            is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            if not is_leap and dt.month > 2:
                doy -= 1
        return doy

def get_baseline_dates():
    """Get all dates from 1992-01-01 to 2002-12-31"""
    start = datetime(1992, 1, 1)
    end = datetime(2002, 12, 31)
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return dates

# Test the function
print("Testing date conversion:")
test_dates = ["1992-01-01", "1992-02-28", "1992-03-01", "2002-12-31"]
for date in test_dates:
    print(f"{date} -> DOY {date_to_doy(date)}")

print("\nBaseline dates count:", len(get_baseline_dates()))