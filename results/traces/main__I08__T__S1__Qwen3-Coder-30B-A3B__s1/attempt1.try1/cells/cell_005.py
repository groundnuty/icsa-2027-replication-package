import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # For leap year handling
    if dt.month == 2 and dt.day == 29:
        return 60
    elif dt.month == 2 and dt.day == 28:
        # Check if it's a leap year - if so, Feb 28 is day 59, else day 59
        year = dt.year
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 60  # In leap year, Feb 28 is day 60 (after Feb 29)
        else:
            return 59  # In non-leap year, Feb 28 is day 59
    
    # Calculate standard day of year
    jan1 = datetime(dt.year, 1, 1)
    doy = (dt - jan1).days + 1
    
    # Adjust for leap year if needed
    if (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0):
        # Leap year: adjust dates after Feb 28
        if dt.month > 2:
            doy += 1
    else:
        # Non-leap year: no adjustment needed
        pass
        
    return doy

def doy_to_date(doy, year=2000):
    """Convert day of year to date (YYYY-MM-DD)"""
    # Create a date for Jan 1 of the given year
    jan1 = datetime(year, 1, 1)
    # Add days to get to the desired DOY
    target_date = jan1 + timedelta(days=doy-1)
    return target_date.strftime("%Y-%m-%d")

# Test the functions more carefully
test_dates = ["2000-01-01", "2000-02-28", "2000-02-29", "2001-02-28", "2000-12-31"]
for date in test_dates:
    doy = date_to_doy(date)
    print(f"{date} -> DOY {doy}")

print("\nTesting reverse conversion for key days:")
for doy in [1, 59, 60, 61, 366]:
    date = doy_to_date(doy)
    print(f"DOY {doy} -> {date}")

# Let's also test our target period
print("\nTarget period:")
start_date = "2007-06-01"
end_date = "2007-08-31"
start_doy = date_to_doy(start_date)
end_doy = date_to_doy(end_date)
print(f"{start_date} -> DOY {start_doy}")
print(f"{end_date} -> DOY {end_doy}")