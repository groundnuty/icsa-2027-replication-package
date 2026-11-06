import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Get all files to check date range
dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(dataset_dir)

# Extract dates from filenames
dates = []
for f in files:
    if f.endswith('.nc'):
        date_str = f.split('_')[1]  # Extract date part like '19820101'
        dates.append(datetime.strptime(date_str, '%Y%m%d'))

dates.sort()
print(f"Date range in dataset: {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}")
print(f"Total files: {len(files)}")

# Check specifically for our target period (2009-06-01 to 2009-08-31)
target_start = datetime(2009, 6, 1)
target_end = datetime(2009, 8, 31)
target_files = [f for f in files if target_start <= datetime.strptime(f.split('_')[1], '%Y%m%d') <= target_end]

print(f"Target period files: {len(target_files)}")
print(f"Target period range: {target_start.strftime('%Y-%m-%d')} to {target_end.strftime('%Y-%m-%d')}")