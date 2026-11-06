import datetime
import numpy as np
import xarray as xr
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

def get_baseline_windows():
    """Get all the windows for baseline calculation including edge cases"""
    # Define baseline period
    baseline_start = '1992-01-01'
    baseline_end = '2002-12-31'
    
    # We need to handle the edge cases where windows extend beyond the baseline period
    # Days 1-366 (leap year support)
    
    # Generate all dates in baseline period
    start_date = datetime.datetime.strptime(baseline_start, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(baseline_end, '%Y-%m-%d')
    
    # For each day of year (1-366), we need to find matching dates within ±5 days
    # But we also need to handle edge cases properly
    
    return start_date, end_date

# Get the files we need
all_files = get_files_needed()
print(f"Found {len(all_files)} files")
print("First 5 files:", all_files[:5])
print("Last 5 files:", all_files[-5:])