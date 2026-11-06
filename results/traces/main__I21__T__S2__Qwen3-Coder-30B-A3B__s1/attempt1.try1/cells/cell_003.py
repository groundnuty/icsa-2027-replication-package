import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert date string to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60
    # Calculate day of year normally
    doy = int(dt.strftime("%j"))
    # Adjust for leap year (29 Feb is treated as day 60)
    if dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        if doy > 59:  # After Feb 28 in leap year
            doy += 1
    return doy

def doy_to_date(doy):
    """Convert day of year back to date string"""
    # We'll construct a non-leap year date for reference
    base_date = datetime(2001, 1, 1)  # Non-leap year
    target_date = base_date + timedelta(days=doy-1)
    return target_date.strftime("%Y-%m-%d")

# Test our conversion
print("Testing date-to-doy conversions:")
test_dates = ["1992-01-01", "1992-02-28", "1992-02-29", "1992-03-01", "2002-12-31"]
for date in test_dates:
    doy = date_to_doy(date)
    print(f"{date} -> DOY {doy}")

print("\nTesting DOY to date conversions:")
test_doy = [1, 59, 60, 61, 366]
for doy in test_doy:
    date = doy_to_date(doy)
    print(f"DOY {doy} -> {date}")