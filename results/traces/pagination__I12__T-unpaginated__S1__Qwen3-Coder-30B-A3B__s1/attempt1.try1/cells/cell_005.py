import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# First, let's find all the files we need for our analysis
fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'

# Get all SST files to determine date range
all_files = fs.ls(base_path)
print(f"Total files found: {len(all_files)}")

# Check first few filenames to understand pattern
for i, f in enumerate(all_files[:5]):
    print(f"File {i}: {f}")

# Get the actual date range by parsing properly
dates = []
for f in all_files:
    if f.endswith('.nc') and 'sst_' in f:
        try:
            # Extract date from filename like sst_19820101.nc
            date_str = f.split('_')[1].split('.')[0]
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            dates.append(date_obj)
        except Exception as e:
            print(f"Error parsing {f}: {e}")

print(f"Available date range: {min(dates)} to {max(dates)}")

# Filter files for baseline period (1992-2002) and target period (2009-06-01 to 2009-08-31)
baseline_files = [f for f in all_files if 'sst_' in f and f.split('_')[1].split('.')[0][:4] >= '1992' and f.split('_')[1].split('.')[0][:4] <= '2002']
target_files = [f for f in all_files if 'sst_' in f and f.split('_')[1].split('.')[0][:4] == '2009']

print(f"Baseline files: {len(baseline_files)}")
print(f"Target files: {len(target_files)}")

# Sort files by date
baseline_files.sort()
target_files.sort()

print("First few baseline files:", baseline_files[:3])
print("First few target files:", target_files[:3])