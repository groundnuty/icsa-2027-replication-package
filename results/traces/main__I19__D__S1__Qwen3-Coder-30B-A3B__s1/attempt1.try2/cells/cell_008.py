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
            filename = f.split('/')[-1]  # Get just the filename
            date_part = filename.split('_')[1].split('.')[0]  # Gets '19820101'
            year = int(date_part[:4])
            if year in baseline_years or year == target_year:
                sst_files.append((f, date_part))
    
    # Sort by date
    sst_files.sort(key=lambda x: x[1])
    
    return sst_files

# Get the files we need
all_files = get_files_needed()
print(f"Found {len(all_files)} files")
print("First 5 files:", all_files[:5])
print("Last 5 files:", all_files[-5:])

# Now let's identify the exact files we need for our periods
baseline_files = [f for f in all_files if int(f[1][:4]) in range(1992, 2003)]
target_files = [f for f in all_files if int(f[1][:4]) == 2014]

print(f"\nBaseline files: {len(baseline_files)}")
print(f"Target files: {len(target_files)}")
print("Baseline files (first 5):", baseline_files[:5])
print("Target files (first 5):", target_files[:5])