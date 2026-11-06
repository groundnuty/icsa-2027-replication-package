
import pandas as pd
import numpy as np
import fsspec
import xarray as xr
import json
import os

os.makedirs('output', exist_ok=True)

fs = fsspec.filesystem('onedata')
data_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# ====== Parameters ======
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21

# ====== Fixed day-of-year mapping ======
def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

# ====== Load dataset ======
with fs.open(data_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat = ds.latitude.values
    lon = ds.longitude.values
    time_vals = ds.time.values
    all_dates = pd.to_datetime(time_vals)
    
    # Region indices
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    # Time indices
    ext_start = pd.Timestamp('1991-12-27')
    ext_end = pd.Timestamp('2003-01-05')
    ext_time_idx = np.where((all_dates >= ext_start) & (all_dates <= ext_end))[0]
    
    tgt_start = pd.Timestamp('2012-06-01')
    tgt_end = pd.Timestamp('2012-08-31')
    tgt_time_idx = np.where((all_dates >= tgt_start) & (all_dates <= tgt_end))[0]
    
    # Load data
    baseline_sst = ds['analysed_sst'].isel(
        time=slice(ext_time_idx[0], ext_time_idx[-1]+1),
        latitude=slice(lat_idx[0], lat_idx[-1]+1),
        longitude=slice(lon_idx[0], lon_idx[-1]+1)
    ).load().values.astype(np.float64)
    
    target_sst = ds['analysed_sst'].isel(
        time=slice(tgt_time_idx[0], tgt_time_idx[-1]+1),
        latitude=slice(lat_idx[0], lat_idx[-1]+1),
        longitude=slice(lon_idx[0], lon_idx[-1]+1)
    ).load().values.astype(np.float64)
    
    region_lat = lat[lat_idx]
    region_lon = lon[lon_idx]
    target_dates = all_dates[tgt_time_idx]

print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")
