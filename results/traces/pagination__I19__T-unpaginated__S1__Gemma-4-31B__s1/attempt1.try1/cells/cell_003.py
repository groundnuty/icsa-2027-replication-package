import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import json
from datetime import datetime, timedelta

def get_doy(dt):
    """Custom day of year mapping: 1 Jan = 1, ..., 29 Feb = 60, ..., 31 Dec = 366"""
    month = dt.month
    day = dt.day
    # Days in months for non-leap year
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month - 1] + day
    if month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        # This is for the standard Julian day.
        # But the requirement is: "29 February = 60, 1 March = 61"
        # Let's re-evaluate.
        pass
    # The prompt says: 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
    # This is exactly the mapping where Feb 29 is always 60, and Mar 1 is always 61, regardless of leap year.
    # Let's use a fixed table.
    month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    # Wait, if 28 Feb is 59, then 29 Feb is 60, 1 Mar is 61.
    # So Jan has 31, Feb has 29.
    # Month starts:
    # Jan: 1
    # Feb: 32
    # Mar: 61 (since Jan 31 + Feb 29 = 60)
    # ...
    # This means we treat every year as if it has a Feb 29 for the purpose of DOY mapping.
    # If it's a non-leap year, Feb 29 just doesn't occur.
    # Let's define it properly.
    month_offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # No, let's use a simpler way.
    # The target is 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
    # This means:
    # Jan: 1-31
    # Feb: 32-60
    # Mar: 61-91
    # etc.
    # This is exactly the DOY of a leap year.
    # Let's use pd.Timestamp(year=2000, month=m, day=d).dayofyear
    return pd.Timestamp(2000, month, day).dayofyear

# Setup coordinates
lat_min, lat_max = 57.13, 58.33
lon_min, lon_max = 22.79, 23.99
target_start = pd.to_datetime("2014-06-01")
target_end = pd.to_datetime("2014-08-31")
baseline_start = pd.to_datetime("1992-01-01")
baseline_end = pd.to_datetime("2002-12-31")

# We need files from 1991-12-27 to 2003-01-05 for baseline pools, and target period.
pool_search_start = baseline_start - timedelta(days=5)
pool_search_end = baseline_end + timedelta(days=5)

fs = fsspec.filesystem('onedata')

def load_region_sst(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords = None
    
    for d in dates:
        filename = f'icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime("%Y%m%d")}.nc'
        try:
            with fs.open(filename, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                # Slice region
                subset = ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                if coords is None:
                    coords = {'latitude': ds.latitude.sel(latitude=slice(lat_min, lat_max)),
                              'longitude': ds.longitude.sel(longitude=slice(lon_min, lon_max))}
                sst_list.append(subset.values)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            # If a file is missing, we might need to handle it. 
            # For this task, we'll assume we can fill it with NaNs or the data is complete.
            # But let's see.
            # Actually, if a file is missing, we should probably append NaNs.
            if coords is None:
                # We don't know the shape yet. We'll have to handle this later.
                sst_list.append(None)
            else:
                sst_list.append(np.full(coords['latitude'].shape[0] * coords['longitude'].shape[0], np.nan).reshape(coords['latitude'].shape[0], coords['longitude'].shape[0]))
    
    if coords is None:
        return None, None, None
    
    sst_array = np.stack(sst_list, axis=0).astype(np.float64)
    return sst_array, coords['latitude'], coords['longitude']

# Since loading all baseline files might be too much, let's be careful.
# Baseline period: 11 years * 365 days ~ 4000 files.
# Each slice is small. (lat_max-lat_min)/0.02 ~ 60, (lon_max-lon_min)/0.02 ~ 60. 60*60*4000 * 8 bytes ~ 115 MB.
# This should fit in memory.

print("Loading baseline data...")
sst_baseline, lats, lons = load_region_sst(pool_search_start, pool_search_end)
print("Loading target data...")
sst_target, _, _ = load_region_sst(target_start, target_end)

print(f"Baseline shape: {sst_baseline.shape}")
print(f"Target shape: {sst_target.shape}")
