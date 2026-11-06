import xarray as xr
import fsspec
import pandas as pd
import os

fs = fsspec.filesystem('onedata')

# Let's see what date range we have in the dataset
date_pattern = '/icsa2027_data_20261101T090944Z/s1z/sst_*.nc'
files = fs.glob(date_pattern)

print(f"Found {len(files)} files")

# Extract dates from filenames
dates = []
for i, file in enumerate(files[:10]):  # Just check first 10 files to verify
    # Extract date from filename like sst_19820101.nc
    date_str = file.split('_')[-1].split('.')[0]  # Get 19820101 from sst_19820101.nc
    date = pd.to_datetime(date_str, format='%Y%m%d')
    dates.append(date)
    if i < 5:  # Print first few for verification
        print(f"File {file} -> Date {date}")

print(f"\nSample dates: {dates[:5]}")

# Try to determine date range
if len(dates) > 0:
    print(f"Date range in dataset: {min(dates)} to {max(dates)}")
    
    # Check if our target period is covered
    target_start = pd.to_datetime('2008-06-01')
    target_end = pd.to_datetime('2008-08-31')
    baseline_start = pd.to_datetime('1992-01-01')
    baseline_end = pd.to_datetime('2002-12-31')

    print(f"\nTarget period: {target_start} to {target_end}")
    print(f"Baseline period: {baseline_start} to {baseline_end}")

    print(f"\nTarget period covered: {target_start >= min(dates) and target_end <= max(dates)}")
    print(f"Baseline period covered: {baseline_start >= min(dates) and baseline_end <= max(dates)}")
else:
    print("No files found matching pattern")