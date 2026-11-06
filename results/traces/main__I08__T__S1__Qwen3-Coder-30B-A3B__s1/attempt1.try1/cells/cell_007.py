import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os

# Set up filesystem
fs = fsspec.filesystem('onedata')

# Function to convert date to DOY
def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # For Feb 29, always return 60 regardless of leap year
    if dt.month == 2 and dt.day == 29:
        return 60
    
    # For Feb 28, check if it's a leap year
    if dt.month == 2 and dt.day == 28:
        # Check if leap year - if so, Feb 28 is day 59, otherwise day 59
        year = dt.year
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        if is_leap:
            return 60  # In leap year, Feb 28 is day 60
        else:
            return 59  # In non-leap year, Feb 28 is day 59
            
    # Standard calculation
    jan1 = datetime(dt.year, 1, 1)
    doy = (dt - jan1).days + 1
    
    # Adjust for leap year if needed (dates after Feb 28)
    if (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0):
        # Leap year: dates after Feb 28 are shifted by 1 day
        if dt.month > 2:
            doy += 1
    
    return doy

# Function to generate all dates in a range
def generate_date_range(start_date, end_date):
    """Generate a list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

# Define region and periods
region = {
    "lat_min": 54.81,
    "lat_max": 56.01,
    "lon_min": 19.61,
    "lon_max": 20.81
}

baseline_period = {"start": "1992-01-01", "end": "2002-12-31"}
target_period = {"start": "2007-06-01", "end": "2007-08-31"}

# Generate date ranges
baseline_dates = generate_date_range(baseline_period["start"], baseline_period["end"])
target_dates = generate_date_range(target_period["start"], target_period["end"])

print(f"Baseline period: {len(baseline_dates)} days")
print(f"Target period: {len(target_dates)} days")

# Check if we have data for the baseline period
print("\nChecking data availability for baseline period...")
# We'll just try to read a few files to confirm data structure
sample_files = []
for year in [1992, 1995, 2000, 2002]:
    for month in [1, 6, 12]:
        for day in [1, 15, 30]:
            date_str = f"{year}-{month:02d}-{day:02d}"
            filename = f"/icsa2027_data_20261101T090944Z/s1z/sst_{year}{month:02d}{day:02d}.nc"
            if fs.exists(filename):
                sample_files.append(filename)
                if len(sample_files) >= 4:
                    break
        if len(sample_files) >= 4:
            break

print(f"Found sample files: {len(sample_files)}")
for f in sample_files:
    print(f"  {f.split('/')[-1]}")