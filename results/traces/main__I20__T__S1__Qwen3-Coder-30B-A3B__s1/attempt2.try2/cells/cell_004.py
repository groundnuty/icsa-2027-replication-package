import xarray as xr
import fsspec
import re

fs = fsspec.filesystem('onedata')

# Get all sst files and extract dates
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
sst_files = [f for f in files if 'sst_' in f]

# Extract dates and sort
dates = []
for f in sst_files:
    match = re.search(r'sst_(\d{8})\.nc', f)
    if match:
        date_str = match.group(1)
        dates.append(date_str)

dates.sort()
print("Date range in dataset:", dates[0], "to", dates[-1])
print("Number of files:", len(dates))