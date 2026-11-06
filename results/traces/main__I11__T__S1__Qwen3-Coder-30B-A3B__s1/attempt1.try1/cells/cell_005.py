import xarray as xr
import fsspec
import numpy as np
from datetime import datetime

fs = fsspec.filesystem('onedata')

# Let's look at date patterns to understand the dataset timeline
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
dates = []

for f in files:
    if f.endswith('.nc'):
        # Extract date from filename
        date_str = f.split('_')[1]  # Format is sst_YYYYMMDD.nc
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            dates.append(date_obj)
        except ValueError:
            continue

dates.sort()
print(f"Date range in dataset: {dates[0]} to {dates[-1]}")
print(f"Total files: {len(dates)}")

# Check if we have enough data for baseline period 1992-2002
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

in_baseline_range = [d for d in dates if baseline_start <= d <= baseline_end]
print(f"Files in baseline range (1992-2002): {len(in_baseline_range)}")
if in_baseline_range:
    print(f"Baseline date range: {min(in_baseline_range)} to {max(in_baseline_range)}")