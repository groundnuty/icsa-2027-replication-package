import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

# Parameters
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
TARGET_START = "2003-06-01"
TARGET_END = "2003-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(base_path)
sst_files = sorted([f for f in all_files if 'sst_' in f and f.endswith('.nc')])

start_baseline_pool = pd.to_datetime(BASELINE_START) - pd.Timedelta(days=5)
end_baseline_pool = pd.to_datetime(BASELINE_END) + pd.Timedelta(days=5)
start_target = pd.to_datetime(TARGET_START)
end_target = pd.to_datetime(TARGET_END)

min_date = min(start_baseline_pool, start_target)
max_date = max(end_baseline_pool, end_target)

needed_files = []
for f in sst_files:
    # Filename is like .../sst_YYYYMMDD.nc
    try:
        date_str = f.split('_')[-1].replace('.nc', '')
        file_date = pd.to_datetime(date_str)
        if min_date <= file_date <= max_date:
            needed_files.append(f)
    except Exception:
        continue

print(f"Total files in dir: {len(sst_files)}")
print(f"Files needed: {len(needed_files)}")
if needed_files:
    print(f"First needed: {needed_files[0]}")
    print(f"Last needed: {needed_files[-1]}")
