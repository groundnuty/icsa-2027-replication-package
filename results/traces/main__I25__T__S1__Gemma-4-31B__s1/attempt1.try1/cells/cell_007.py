import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_doy(date):
    """Custom DOY mapping as per instructions."""
    month = date.month
    day = date.day
    if month == 1:
        return day
    elif month == 2:
        # Feb 28 = 59, Feb 29 = 60
        return 31 + day
    elif month == 3:
        # Mar 1 = 61 (if Feb 29 exists) or 61 (if not)
        # The instructions say: 28 Feb = 59, 29 Feb = 60, 1 March = 61.
        # This is a fixed calendar mapping.
        # Let's use a fixed table for month starts.
        # Jan: 1, Feb: 32, Mar: 61 (since Feb has 29 in this mapping), ...
        # Wait, "Non-leap years have no day 60."
        # This means for a non-leap year, March 1 is still day 61? 
        # Let's re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
        # This implies the DOY is based on a leap year calendar.
        pass

def get_custom_doy(date):
    # Cumulative days in a leap year
    month_starts = {
        1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153, 
        7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336
    }
    doy = month_starts[date.month] + date.day - 1
    # For non-leap years, 29 Feb doesn't exist. 
    # The mapping is simple: 1 Jan -> 1, ..., 28 Feb -> 59, 1 Mar -> 61...
    # This is exactly what my logic does.
    # Let's verify:
    # Jan 1: 1 + 1 - 1 = 1. Correct.
    # Feb 28: 32 + 28 - 1 = 59. Correct.
    # Feb 29: 32 + 29 - 1 = 60. Correct.
    # Mar 1: 61 + 1 - 1 = 61. Correct.
    # Dec 31: 336 + 31 - 1 = 366. Correct.
    return doy

# Define the region and target period
lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45
target_start = pd.to_datetime("2016-06-01")
target_end = pd.to_datetime("2016-08-31")
baseline_start_year = 1992
baseline_end_year = 2002

# Dates for the baseline pool
# Need SST from 1991-12-27 to 2003-01-05
baseline_pool_start = pd.to_datetime("1991-12-27")
baseline_pool_end = pd.to_datetime("2003-01-05")

# Target dates
target_dates = pd.date_range(target_start, target_end)

# Baseline dates for pool calculations (the B_y,d's)
# We need to find all dates in 1992-2002 and their custom DOY
all_baseline_dates = pd.date_range(pd.to_datetime(f"{baseline_start_year}-01-01"), 
                                   pd.to_datetime(f"{baseline_end_year}-12-31"))

# Map each baseline date to its custom DOY
baseline_date_to_doy = {date: get_custom_doy(date.to_pydatetime()) for date in all_baseline_dates}

# Identify all files needed
fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

def get_file_path(date):
    return f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"

# Necessary files: baseline pool range + target range
all_needed_dates = sorted(list(pd.date_range(baseline_pool_start, baseline_pool_end)) + 
                          list(target_dates))
all_needed_dates = sorted(list(set(all_needed_dates)))

# Let's check if all files exist
missing_files = []
for date in all_needed_dates:
    path = get_file_path(date)
    if not fs.exists(path):
        missing_files.append(path)

if missing_files:
    print(f"Missing files: {len(missing_files)}")
    print(missing_files[:10])
else:
    print("All necessary files found.")
