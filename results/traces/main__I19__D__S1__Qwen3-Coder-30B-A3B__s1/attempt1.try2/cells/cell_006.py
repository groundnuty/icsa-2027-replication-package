import datetime
import numpy as np
import xarray as xr
import fsspec
import os
from pathlib import Path

def get_files_needed():
    """Identify all files needed for baseline (1992-2002) and target period (2014-06-01 to 2014-08-31)"""
    
    # Get all files in the directory
    fs = fsspec.filesystem('onedata')
    files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
    
    # Filter for the specific years we need
    baseline_years = list(range(1992, 2003))  # 1992-2002 inclusive
    target_year = 2014
    
    # Extract dates from filenames
    sst_files = []
    for f in files:
        if f.endswith('.nc'):
            # Extract date from filename like sst_19820101.nc
            date_part = f.split('_')[1].split('.')[0]  # Gets '19820101'
            year = int(date_part[:4])
            if year in baseline_years or year == target_year:
                sst_files.append((f, date_part))
    
    # Sort by date
    sst_files.sort(key=lambda x: x[1])
    
    return sst_files

def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.timetuple().tm_yday

def get_all_dates_in_period(start_date, end_date):
    """Generate all dates in a period"""
    start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += datetime.timedelta(days=1)
    
    return dates

# Get the files we need
all_files = get_files_needed()
print(f"Found {len(all_files)} files")
print("First 5 files:", all_files[:5])
print("Last 5 files:", all_files[-5:])

# Check some key dates
baseline_period = '1992-01-01 to 2002-12-31'
target_period = '2014-06-01 to 2014-08-31'

print(f"\nBaseline period: {baseline_period}")
print(f"Target period: {target_period}")

# Get all dates in baseline period
baseline_dates = get_all_dates_in_period('1992-01-01', '2002-12-31')
print(f"Total baseline dates: {len(baseline_dates)}")

# Get all dates in target period
target_dates = get_all_dates_in_period('2014-06-01', '2014-08-31')
print(f"Total target dates: {len(target_dates)}")