import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Define region boundaries
LAT_MIN, LAT_MAX = 57.83, 59.03
LON_MIN, LON_MAX = 17.41, 18.61

# Define target period
TARGET_START = datetime(2008, 6, 1)
TARGET_END = datetime(2008, 8, 31)
TARGET_DAYS = [(TARGET_START + timedelta(days=i)) for i in range((TARGET_END - TARGET_START).days + 1)]

# Define baseline period  
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
BASELINE_DAYS = [(BASELINE_START + timedelta(days=i)) for i in range((BASELINE_END - BASELINE_START).days + 1)]

# Function to convert date to day of year (1-366)
def date_to_doy(date):
    # Convert to datetime if it's a date object
    if hasattr(date, 'year'):
        doy = date.timetuple().tm_yday
        # Handle leap year special case for Feb 29
        if date.month > 2 and ((date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0)):
            if doy >= 60:  # After Feb 29, adjust day numbers
                doy += 1
        return doy
    else:
        # If it's already a datetime object
        doy = date.timetuple().tm_yday
        if date.month > 2 and ((date.year % 4 == 0 and date.year % 100 != 0) or (date.year % 400 == 0)):
            if doy >= 60:
                doy += 1
        return doy

# Function to get the range of dates for a specific day of year
def get_baseline_window_dates(doy, base_start, base_end):
    """Get all dates within ±5 days of any date with the given day of year"""
    window_dates = []
    
    # Check if this is a leap year day (day 60)
    is_leap_day = (doy == 60)
    
    # Get all dates in baseline period
    for date in BASELINE_DAYS:
        date_doy = date_to_doy(date)
        
        # Special handling for day 60 (Feb 29) - it belongs to neighbors
        if is_leap_day:
            # For day 60, we want to include the dates that would normally be assigned to day 60
            # But in our case, we're just skipping day 60 itself since it's not a valid day in non-leap years
            continue
            
        # Check if date falls within the window around doy
        if abs(date_doy - doy) <= 5:
            window_dates.append(date)
    
    # Also handle edge cases for beginning and end of baseline period
    # This part handles cases where the window goes beyond the baseline period
    # But for now we'll keep it simple
    
    return window_dates

# Test the conversion function
test_date = datetime(2008, 2, 29)  # A leap year date
print(f"Date {test_date} -> DOY: {date_to_doy(test_date)}")

test_date2 = datetime(2008, 3, 1)  # Not a leap year date
print(f"Date {test_date2} -> DOY: {date_to_doy(test_date2)}")