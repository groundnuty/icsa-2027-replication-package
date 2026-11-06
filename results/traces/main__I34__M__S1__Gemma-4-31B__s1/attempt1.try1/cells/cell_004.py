import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# Parameters
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89
target_start_str = '2007-06-01'
target_end_str = '2007-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'

target_start = pd.to_datetime(target_start_str)
target_end = pd.to_datetime(target_end_str)
baseline_start = pd.to_datetime(baseline_start_str)
baseline_end = pd.to_datetime(baseline_end_str)

dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def load_sst_region(start, end):
    dates = pd.date_range(start, end)
    sst_list = []
    valid_dates = []
    
    # Pre-check first file to get coords
    first_date_str = dates[0].strftime('%Y%m%d')
    first_file = os.path.join(dataset_dir, f"sst_{first_date_str}.nc")
    if not os.path.exists(first_file):
        # Try to find any existing file to get coordinates if the first one is missing
        # but for this task, we assume the requested range is mostly available.
        # Let's just search.
        pass

    lat_vals = None
    lon_vals = None

    for date in dates:
        filename = f"sst_{date.strftime('%Y%m%d')}.nc"
        path = os.path.join(dataset_dir, filename)
        if os.path.exists(path):
            with xr.open_dataset(path, engine="h5netcdf") as ds:
                region_ds = ds.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                if lat_vals is None:
                    lat_vals = region_ds.latitude.values
                    lon_vals = region_ds.longitude.values
                
                sst_list.append(region_ds.analysed_sst.values.squeeze())
                valid_dates.append(date)
        else:
            # If a file is missing, we can't just skip it if we want a continuous time series for baseline
            # But let's see. The method says "every SST value whose date lies within...".
            # So missing files just mean fewer values in the pool.
            pass
    
    if not sst_list:
        return None, None, None, None
    
    return np.array(sst_list, dtype=np.float64), valid_dates, lat_vals, lon_vals

print("Loading baseline data...")
# Baseline pool needs +/- 5 days window.
# The range of baseline dates is 1992-01-01 to 2002-12-31.
# Window extends to 1991-12-27 and 2003-01-05.
sst_baseline, dates_baseline, lat_vals, lon_vals = load_sst_region(baseline_start - timedelta(days=5), baseline_end + timedelta(days=5))
print("Loading target data...")
sst_target, dates_target, _, _ = load_sst_region(target_start, target_end)

# target_start to target_end inclusive
target_dates_expected = pd.date_range(target_start, target_end)
# Filter target_dates to only those we actually loaded
dates_target = [d for d in dates_target if d >= target_start and d <= target_end]
sst_target = sst_target[[i for i, d in enumerate(dates_target) if d in dates_target]] # This is wrong.
# Let's reload target specifically.
