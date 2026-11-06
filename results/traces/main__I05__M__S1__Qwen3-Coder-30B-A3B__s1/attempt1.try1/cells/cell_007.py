import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Define region and period
LAT_MIN, LAT_MAX = 54.39, 55.59
LON_MIN, LON_MAX = 18.25, 19.45
START_DATE = datetime(2021, 6, 1)
END_DATE = datetime(2021, 8, 31)
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)

# Create output directory
os.makedirs('output', exist_ok=True)

def date_to_doy(date):
    """Convert a date to day-of-year (1-366)"""
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap year if needed
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        if doy >= 60:  # After Feb 29
            doy += 1
            
    return doy

# Test the date conversion
test_dates = [
    datetime(2021, 1, 1),   # Should be day 1
    datetime(2021, 2, 28),  # Should be day 59  
    datetime(2021, 3, 1),   # Should be day 61
    datetime(2020, 2, 29),  # Leap year - should be day 60
]

print("Testing date to DOY conversion:")
for d in test_dates:
    print(f"{d.strftime('%Y-%m-%d')} -> DOY {date_to_doy(d)}")

print("\nRegion: lat {LAT_MIN} to {LAT_MAX}°N, lon {LON_MIN} to {LON_MAX}°E")
print(f"Target period: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
print(f"Baseline period: {BASELINE_START.strftime('%Y-%m-%d')} to {BASELINE_END.strftime('%Y-%m-%d')}")