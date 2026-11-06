import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

# Function to convert date to day of year (1-366)
def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # Handle leap year cases properly
    if dt.month == 2 and dt.day == 29:
        return 60  # February 29th is day 60
    
    # Create a date for Jan 1 of the same year to calculate day of year
    jan1 = datetime(dt.year, 1, 1)
    doy = (dt - jan1).days + 1
    
    # Adjust for leap year if needed
    if dt.month > 2 and (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0)):
        if doy >= 60:  # If it's after Feb 28 in a leap year
            doy += 1
    
    return doy

# Test the function
test_dates = ['1992-01-01', '1992-02-28', '1992-02-29', '1992-03-01', '2002-12-31']
for date in test_dates:
    print(f"{date} -> day of year: {date_to_doy(date)}")

# Download a few more files to see data pattern
fs = fsspec.filesystem('onedata')

# Get a few files for the baseline period (1992-2002)
baseline_files = []
for year in range(1992, 2003):
    for month in range(1, 13):
        # Generate all dates in the baseline period
        if month in [1, 3, 5, 7, 8, 10, 12]:
            days_in_month = 31
        elif month in [4, 6, 9, 11]:
            days_in_month = 30
        else:  # February
            days_in_month = 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
            
        for day in range(1, days_in_month + 1):
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            remote_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{year:04d}{month:02d}{day:02d}.nc'
            try:
                fs.get(remote_path, f'/work/sst_{year:04d}{month:02d}{day:02d}.nc')
                baseline_files.append((date_str, remote_path))
            except Exception as e:
                pass  # File doesn't exist

print(f"Found {len(baseline_files)} baseline files")