import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

def get_date_range_from_filename(filename):
    """Extract date from filename like sst_19820101.nc"""
    date_str = filename.split('_')[1].split('.')[0]  # Extract date part
    return datetime.strptime(date_str, '%Y%m%d')

def get_all_files_in_date_range(start_date, end_date):
    """Get all files in the given date range"""
    fs = fsspec.filesystem('onedata')
    files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
    
    # Filter files by date range
    filtered_files = []
    for f in files:
        if f.startswith('sst_'):
            try:
                file_date = get_date_range_from_filename(f)
                if start_date <= file_date <= end_date:
                    filtered_files.append(f)
            except:
                continue
    
    return sorted(filtered_files)

# Get baseline period files (1992-01-01 to 2002-12-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_files = get_all_files_in_date_range(baseline_start, baseline_end)

print(f"Found {len(baseline_files)} baseline files")
print(f"Baseline period: {baseline_start.strftime('%Y-%m-%d')} to {baseline_end.strftime('%Y-%m-%d')}")

# Get target period files (2016-06-01 to 2016-08-31)
target_start = datetime(2016, 6, 1)
target_end = datetime(2016, 8, 31)
target_files = get_all_files_in_date_range(target_start, target_end)

print(f"Found {len(target_files)} target files")
print(f"Target period: {target_start.strftime('%Y-%m-%d')} to {target_end.strftime('%Y-%m-%d')}")

# Define our region of interest
lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

print(f"\nRegion of interest: lat {lat_min} to {lat_max}°N, lon {lon_min} to {lon_max}°E")