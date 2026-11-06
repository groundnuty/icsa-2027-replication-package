import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
from datetime import datetime, timedelta

# Region and period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start = pd.Timestamp('2012-06-01')
target_end = pd.Timestamp('2012-08-31')
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

def get_doy(dt):
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    # Non-leap years have no day 60.
    # pandas.Timestamp.dayofyear does this (1-indexed).
    return dt.dayofyear

def load_sst_region(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords = None
    
    for date in dates:
        filename = f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        with fs.open(filename, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            # Subset to region
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            )
            if coords is None:
                coords = {
                    'latitude': subset.latitude.values,
                    'longitude': subset.longitude.values,
                    'time': dates
                }
            sst_list.append(subset.values)
    
    return np.array(sst_list, dtype='float64'), coords

# Load target data
target_sst, target_coords = load_sst_region(target_start, target_end)
print(f"Target SST shape: {target_sst.shape}")

# Load baseline data. 
# We need a slightly wider range for the windows (+/- 5 days)
# Baseline is 1992-01-01 to 2002-12-31. 
# Windows can extend to 1991-12-27 and 2003-01-05.
baseline_load_start = baseline_start - pd.Timedelta(days=5)
baseline_load_end = baseline_end + pd.Timedelta(days=5)
baseline_sst, baseline_coords = load_sst_region(baseline_load_start, baseline_load_end)
print(f"Baseline SST shape: {baseline_sst.shape}")
