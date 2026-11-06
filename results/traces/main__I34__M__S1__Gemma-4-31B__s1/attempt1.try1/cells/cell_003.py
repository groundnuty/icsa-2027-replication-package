import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# Parameters
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89
target_start = pd.to_datetime('2007-06-01')
target_end = pd.to_datetime('2007-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')

# Baseline window extension
baseline_ext_start = baseline_start - timedelta(days=5)
baseline_ext_end = baseline_end + timedelta(days=5)

# Directory
dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def get_sst_for_period(start, end):
    dates = pd.date_range(start, end)
    sst_list = []
    valid_dates = []
    
    for date in dates:
        filename = f"sst_{date.strftime('%Y%m%d')}.nc"
        path = os.path.join(dataset_dir, filename)
        if os.path.exists(path):
            with xr.open_dataset(path, engine="h5netcdf") as ds:
                # Slice region
                region_ds = ds.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                sst_list.append(region_ds.analysed_sst.values)
                valid_dates.append(date)
        else:
            print(f"Missing file: {filename}")
    
    if not sst_list:
        return None, None
    
    # Create an xarray Dataset for convenience
    sst_array = np.array(sst_list)
    # Assuming all files have the same coords
    with xr.open_dataset(os.path.join(dataset_dir, f"sst_{dates[0].strftime('%Y%m%d')}.nc"), engine="h5netcdf") as ds:
        lat = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max)).latitude.values
        lon = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max)).longitude.values
    
    ds_result = xr.Dataset(
        {"sst": (["time", "latitude", "longitude"], sst_array)},
        coords={"time": valid_dates, "latitude": lat, "longitude": lon}
    )
    return ds_result, valid_dates

# Load baseline and target data
print("Loading baseline data...")
ds_baseline, dates_baseline = get_sst_for_period(baseline_ext_start, baseline_ext_end)
print("Loading target data...")
ds_target, dates_target = get_sst_for_period(target_start, target_end)

if ds_baseline is None or ds_target is None:
    print("Error: Could not load necessary data.")
else:
    print(f"Baseline loaded: {dates_baseline[0]} to {dates_baseline[-1]}")
    print(f"Target loaded: {dates_target[0]} to {dates_target[-1]}")
    
    # Keep as a reference for the next step
    # Let's save them to disk if they are large, but they should fit in memory
    # We'll proceed with the calculation in the next block.
