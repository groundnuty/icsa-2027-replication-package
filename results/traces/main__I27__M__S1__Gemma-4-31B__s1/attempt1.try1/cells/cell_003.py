import os
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta

# Define parameters
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61
target_start = "2008-06-01"
target_end = "2008-08-31"
baseline_start = "1992-01-01"
baseline_end = "2002-12-31"

# Windows range
baseline_pool_start = "1991-12-27"
baseline_pool_end = "2003-01-05"

def get_date_range(start_str, end_str):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    return pd.date_range(start, end)

baseline_pool_dates = get_date_range(baseline_pool_start, baseline_pool_end)
target_dates = get_date_range(target_start, target_end)

# Identify files
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
all_files = os.listdir(data_dir)

def date_to_filename(d):
    return f"sst_{d.strftime('%Y%m%d')}.nc"

needed_filenames = {date_to_filename(d) for d in baseline_pool_dates} | {date_to_filename(d) for d in target_dates}
available_needed_files = [f for f in all_files if f in needed_filenames]

print(f"Total files needed: {len(needed_filenames)}")
print(f"Total files available: {len(available_needed_files)}")

# Check for missing files
missing_files = needed_filenames - set(available_needed_files)
if missing_files:
    print(f"Missing files: {len(missing_files)}")
    # Sort and print a few to see which ones are missing
    for mf in sorted(list(missing_files))[:10]:
        print(mf)
else:
    print("All needed files are available.")
