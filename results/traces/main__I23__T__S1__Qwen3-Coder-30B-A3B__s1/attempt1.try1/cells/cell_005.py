import xarray as xr
import fsspec
import numpy as np
from datetime import datetime

fs = fsspec.filesystem('onedata')

# Get all files and sort them by date
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
date_files = []

for f in files:
    if f.endswith('.nc'):
        # Extract date from filename
        date_str = f.split('_')[1]  # Format: sst_YYYYMMDD.nc
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            date_files.append((date_obj, f))
        except ValueError:
            continue

# Sort by date
date_files.sort()

print(f"Total files: {len(date_files)}")
print(f"Date range: {date_files[0][0].strftime('%Y-%m-%d')} to {date_files[-1][0].strftime('%Y-%m-%d')}")

# Show a few sample dates
print("\nFirst 5 files:")
for i in range(min(5, len(date_files))):
    print(f"  {date_files[i][0].strftime('%Y-%m-%d')} - {date_files[i][1]}")

print("\nLast 5 files:")
for i in range(max(0, len(date_files)-5), len(date_files)):
    print(f"  {date_files[i][0].strftime('%Y-%m-%d')} - {date_files[i][1]}")