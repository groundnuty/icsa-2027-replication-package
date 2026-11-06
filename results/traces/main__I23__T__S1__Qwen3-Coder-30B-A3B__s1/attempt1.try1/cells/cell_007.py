import xarray as xr
import fsspec
import numpy as np
from datetime import datetime
import re

fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'

# Get all files and extract dates
date_pattern = re.compile(r'sst_(\d{8})\.nc')

def extract_date_from_filename(filename):
    match = date_pattern.search(filename)
    if match:
        date_str = match.group(1)
        return datetime.strptime(date_str, '%Y%m%d')
    return None

# Get all files with their dates
date_files = []
for f in fs.ls(base_path):
    if f.endswith('.nc'):
        date_obj = extract_date_from_filename(f)
        if date_obj:
            date_files.append((date_obj, f))

# Sort by date
date_files.sort()

print(f"Total files: {len(date_files)}")
if date_files:
    print(f"Date range: {date_files[0][0].strftime('%Y-%m-%d')} to {date_files[-1][0].strftime('%Y-%m-%d')}")

# Check if we have data for our required baseline period (1992-2002)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

baseline_files = [f for d, f in date_files if baseline_start <= d <= baseline_end]
print(f"Baseline files (1992-2002): {len(baseline_files)}")

# Check if we have data for our target period (2013-06-01 to 2013-08-31)
target_start = datetime(2013, 6, 1)
target_end = datetime(2013, 8, 31)
target_files = [f for d, f in date_files if target_start <= d <= target_end]
print(f"Target files (2013-06-01 to 2013-08-31): {len(target_files)}")