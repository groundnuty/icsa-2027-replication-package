import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    doy = int(dt.strftime("%j"))  # Day of year (1-365)
    # Handle leap year special case for Feb 29
    if dt.month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        # This is a leap year and we're past Feb 28
        if doy >= 60:  # If it's after Feb 29, adjust by 1
            doy += 1
    return doy

def doy_to_date(doy, year=2000):
    """Convert day of year to YYYY-MM-DD string (using 2000 as reference year)"""
    dt = datetime(year, 1, 1) + timedelta(days=doy-1)
    return dt.strftime("%Y-%m-%d")

# Test the conversion
print("Testing date conversions:")
test_dates = ["1992-01-01", "2002-12-31", "1992-02-28", "1992-02-29", "1993-02-28"]
for date in test_dates:
    doy = date_to_doy(date)
    print(f"{date} -> DOY {doy}")
    
print("\nTesting reverse conversion:")
for doy in [1, 59, 60, 61, 365]:
    date = doy_to_date(doy)
    print(f"DOY {doy} -> {date}")