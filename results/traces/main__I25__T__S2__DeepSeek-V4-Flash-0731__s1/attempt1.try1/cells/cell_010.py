
import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import os

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat_idx = np.where((ds.latitude.values >= 57.57) & (ds.latitude.values <= 58.77))[0]
    lon_idx = np.where((ds.longitude.values >= 10.25) & (ds.longitude.values <= 11.45))[0]
    
    # Load baseline data (1991-12-27 to 2003-01-05)
    b_start = np.datetime64('1991-12-27')
    b_end = np.datetime64('2003-01-05')
    time_vals = ds.time.values
    b_mask = (time_vals >= b_start) & (time_vals <= b_end)
    b_idx = np.where(b_mask)[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=b_idx, latitude=lat_idx, longitude=lon_idx
    ).values
    baseline_time = time_vals[b_idx]
    
    # Load target data
    t_start = np.datetime64('2016-06-01')
    t_end = np.datetime64('2016-08-31')
    t_mask = (time_vals >= t_start) & (time_vals <= t_end)
    t_idx = np.where(t_mask)[0]
    
    target_sst = ds['analysed_sst'].isel(
        time=t_idx, latitude=lat_idx, longitude=lon_idx
    ).values
    target_time = time_vals[t_idx]

# Convert numpy datetime64 to datetime objects
baseline_dt = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
target_dt = [pd.Timestamp(t).to_pydatetime() for t in target_time]

print(f"Baseline: {len(baseline_dt)} dates from {baseline_dt[0]} to {baseline_dt[-1]}")
print(f"Target: {len(target_dt)} dates from {target_dt[0]} to {target_dt[-1]}")
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Target SST shape: {target_sst.shape}")

# Identify sea cells: SST finite on every day of target period
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_mask.sum()} out of {sea_mask.size}")
