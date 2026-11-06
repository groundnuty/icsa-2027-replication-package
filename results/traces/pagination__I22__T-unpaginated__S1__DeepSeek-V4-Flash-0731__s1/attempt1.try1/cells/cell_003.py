
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# List all files to understand available dates
files = fs.ls(base)
print(f'Total files: {len(files)}')
# Extract dates
import re
dates = []
for f in files:
    m = re.search(r'sst_(\d{8})\.nc', f)
    if m:
        dates.append(m.group(1))
dates.sort()
print(f'First: {dates[0]}, Last: {dates[-1]}')
print(f'Count: {len(dates)}')

# Check what years are available
years = set(d[:4] for d in dates)
print(f'Years: {sorted(years)}')
