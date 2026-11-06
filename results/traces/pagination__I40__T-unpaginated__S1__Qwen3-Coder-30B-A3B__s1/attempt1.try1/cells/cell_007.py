import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Get all files to check date range
dataset_dir = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(dataset_dir)

print("Sample filenames:")
for i, f in enumerate(files[:5]):
    print(f"  {f}")

# Check specifically for our target period (2009-06-01 to 2009-08-31)
target_start = datetime(2009, 6, 1)
target_end = datetime(2009, 8, 31)

# Filter files for the target period
target_files = []
for f in files:
    if f.endswith('.nc'):
        # Extract date from filename - they seem to be in format like sst_19820101.nc
        try:
            date_part = f.split('_')[1].split('.')[0]  # Extract '19820101' from 'sst_19820101.nc'
            file_date = datetime.strptime(date_part, '%Y%m%d')
            if target_start <= file_date <= target_end:
                target_files.append(f)
        except Exception as e:
            print(f"Error parsing {f}: {e}")

print(f"\nTarget period files: {len(target_files)}")
print(f"Target period range: {target_start.strftime('%Y-%m-%d')} to {target_end.strftime('%Y-%m-%d')}")

# Check baseline period (1992-2002)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_files = []
for f in files:
    if f.endswith('.nc'):
        try:
            date_part = f.split('_')[1].split('.')[0]
            file_date = datetime.strptime(date_part, '%Y%m%d')
            if baseline_start <= file_date <= baseline_end:
                baseline_files.append(f)
        except Exception as e:
            pass

print(f"Baseline period files: {len(baseline_files)}")
print(f"Baseline period range: {baseline_start.strftime('%Y-%m-%d')} to {baseline_end.strftime('%Y-%m-%d')}")