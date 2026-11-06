
import pandas as pd
import numpy as np
import fsspec
import xarray as xr
import json
import os

# ====== Setup ======
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
    
    # Find region indices
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    print(f"Region: lat indices {lat_idx[0]}-{lat_idx[-1]}, lon indices {lon_idx[0]}-{lon_idx[-1]}")
    print(f"Region lat values: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}")
    print(f"Region lon values: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}")
    
    # Time indices
    all_dates = pd.to_datetime(time_vals)
    
    # Extended baseline: 1991-12-27 to 2003-01-05
    ext_start = pd.Timestamp('1991-12-27')
    ext_end = pd.Timestamp('2003-01-05')
    ext_time_mask = (all_dates >= ext_start) & (all_dates <= ext_end)
    ext_time_idx = np.where(ext_time_mask)[0]
    
    # Target: 2012-06-01 to 2012-08-31
    tgt_start = pd.Timestamp('2012-06-01')
    tgt_end = pd.Timestamp('2012-08-31')
    tgt_time_mask = (all_dates >= tgt_start) & (all_dates <= tgt_end)
    tgt_time_idx = np.where(tgt_time_mask)[0]
    
    print(f"Extended baseline time indices: {ext_time_idx[0]}-{ext_time_idx[-1]}, count={len(ext_time_idx)}")
    print(f"Target time indices: {tgt_time_idx[0]}-{tgt_time_idx[-1]}, count={len(tgt_time_idx)}")
    
    # Load baseline and target data for the region
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
    
    print(f"Baseline data shape: {baseline_sst.shape}")
    print(f"Target data shape: {target_sst.shape}")

# ====== Determine sea cells ======
# A sea cell has finite SST on every day of the target period
n_lat, n_lon = len(lat_idx), len(lon_idx)
sea_cells = np.ones((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if np.any(np.isnan(target_sst[:, i, j])):
            sea_cells[i, j] = False

print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")
print(f"Land cells: {(~sea_cells).sum()}")
