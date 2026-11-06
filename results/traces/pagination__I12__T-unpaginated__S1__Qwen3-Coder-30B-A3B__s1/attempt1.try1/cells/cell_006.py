import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os
import re

# Create output directory
os.makedirs('output', exist_ok=True)

# First, let's find all the files we need for our analysis
fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'

# Get all SST files to determine date range
all_files = fs.ls(base_path)
print(f"Total files found: {len(all_files)}")

# Extract just the filenames properly
filenames = []
for item in all_files:
    # Extract just the filename part after the last slash
    filename = item.split('/')[-1]
    if filename.endswith('.nc') and 'sst_' in filename:
        filenames.append(filename)

print(f"Valid SST files: {len(filenames)}")
print("First few filenames:", filenames[:5])

# Parse dates from filenames
dates = []
for filename in filenames:
    try:
        # Extract date from filename like sst_19820101.nc
        date_str = re.search(r'sst_(\d{8})\.nc', filename).group(1)
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        dates.append(date_obj)
    except Exception as e:
        print(f"Error parsing {filename}: {e}")

print(f"Available date range: {min(dates)} to {max(dates)}")

# Filter files for baseline period (1992-2002) and target period (2009-06-01 to 2009-08-31)
baseline_files = [f for f in filenames if re.search(r'sst_(\d{8})\.nc', f).group(1)[:4] >= '1992' and re.search(r'sst_(\d{8})\.nc', f).group(1)[:4] <= '2002']
target_files = [f for f in filenames if re.search(r'sst_(\d{8})\.nc', f).group(1)[:4] == '2009']

print(f"Baseline files: {len(baseline_files)}")
print(f"Target files: {len(target_files)}")

# Sort files by date
baseline_files.sort()
target_files.sort()

print("First few baseline files:", baseline_files[:3])
print("First few target files:", target_files[:3])