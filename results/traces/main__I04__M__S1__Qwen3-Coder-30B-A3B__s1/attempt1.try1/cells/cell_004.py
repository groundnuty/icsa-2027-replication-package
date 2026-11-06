import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    doy = int(dt.strftime("%j"))
    # Handle leap year special case for Feb 29
    if dt.month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        # If it's a leap year and we're past Feb 29, adjust day numbers
        if doy >= 60:  # Feb 29 is day 60
            doy -= 1
    return doy

def doy_to_date(doy, year=2000):
    """Convert day-of-year to YYYY-MM-DD string (using 2000 as dummy year)"""
    dt = datetime(year, 1, 1) + timedelta(days=doy-1)
    return dt.strftime("%Y-%m-%d")

# Test our function
print("Testing date conversion:")
test_dates = ["2020-01-01", "2020-02-28", "2020-02-29", "2020-03-01", "2020-12-31"]
for date in test_dates:
    doy = date_to_doy(date)
    print(f"{date} -> DOY {doy}")

print("\nTesting reverse conversion:")
test_doy = [1, 59, 60, 61, 366]
for doy in test_doy:
    date = doy_to_date(doy)
    print(f"DOY {doy} -> {date}")