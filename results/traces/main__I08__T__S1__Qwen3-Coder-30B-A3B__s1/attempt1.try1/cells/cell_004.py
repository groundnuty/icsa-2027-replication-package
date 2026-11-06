import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60
    elif dt.month == 2 and dt.day == 28:
        # Check if it's a leap year
        year = dt.year
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 60
        else:
            # Not a leap year, treat as day 59
            return 59
    
    # For regular dates, calculate day of year
    doy = (dt - datetime(dt.year, 1, 1)).days + 1
    # Special case for Feb 29 (should be 60)
    if dt.month > 2:
        # Adjust for leap year if needed
        if (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0):
            if dt.month == 3 and dt.day == 1:
                return 61
            elif dt.month > 3:
                return doy + 1
    return doy

def doy_to_date(doy, year=2000):
    """Convert day of year to date (YYYY-MM-DD)"""
    # Create a date for Jan 1 of the given year
    jan1 = datetime(year, 1, 1)
    # Add days to get to the desired DOY
    target_date = jan1 + timedelta(days=doy-1)
    return target_date.strftime("%Y-%m-%d")

# Test the functions
test_dates = ["2000-01-01", "2000-02-28", "2000-02-29", "2001-02-28", "2000-12-31"]
for date in test_dates:
    doy = date_to_doy(date)
    print(f"{date} -> DOY {doy}")

print("\nTesting reverse conversion:")
for doy in [1, 59, 60, 61, 366]:
    date = doy_to_date(doy)
    print(f"DOY {doy} -> {date}")