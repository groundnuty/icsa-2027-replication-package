import xarray as xr
import fsspec
import os
import glob
from datetime import datetime, timedelta

# Check all available files to determine the time range
fs = fsspec.filesystem('onedata')
base_path = '/icsa2027_data_20261101T090944Z/s1z'
files = fs.glob(base_path + '/sst_*.nc')
print(f"Found {len(files)} files")

# Extract dates from filenames
dates = []
for file in files[:10]:  # Just check first 10 for now
    filename = os.path.basename(file)
    date_str = filename.split('_')[1][:8]  # Extract YYYYMMDD part
    dates.append(datetime.strptime(date_str, '%Y%m%d'))

print("Sample dates:", sorted(dates)[:5])
print("Total date range:", min(dates), "to", max(dates))