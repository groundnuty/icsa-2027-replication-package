import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Define our region of interest
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75

# Define baseline period
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)

# Define target period  
TARGET_START = datetime(2009, 6, 1)
TARGET_END = datetime(2009, 8, 31)

def date_to_doy(date):
    """Convert date to day of year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    # Adjust for leap year if needed
    if date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        if doy > 59:  # After Feb 28 in leap year
            doy += 1
    return doy

def get_baseline_dates():
    """Generate all dates in baseline period"""
    dates = []
    current = BASELINE_START
    while current <= BASELINE_END:
        dates.append(current)
        current += timedelta(days=1)
    return dates

def get_window_dates(doy, baseline_dates):
    """Get dates that fall within ±5 days of a DOY in baseline period"""
    window_dates = []
    for date in baseline_dates:
        date_doy = date_to_doy(date)
        if date_doy == doy:
            # Check if date is within ±5 days
            if abs((date - datetime(date.year, 1, 1)).days) <= 5 or \
               abs((datetime(date.year, 12, 31) - date).days) <= 5:
                window_dates.append(date)
        elif doy == 60 and date.month == 2 and date.day == 28:
            # Special case for day 60 (Feb 28) 
            window_dates.append(date)
        elif doy == 60 and date.month == 3 and date.day == 1:
            # Special case for day 60 (Mar 1)
            window_dates.append(date)
    return window_dates

# Get baseline dates
baseline_dates = get_baseline_dates()
print(f"Baseline period: {len(baseline_dates)} days")

# Test date conversion
test_date = datetime(2000, 2, 29)  # Leap year
print(f"Date {test_date} DOY: {date_to_doy(test_date)}")

test_date = datetime(2000, 3, 1)  # Regular date
print(f"Date {test_date} DOY: {date_to_doy(test_date)}")