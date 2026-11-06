import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'

# Region bounds
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89

# Target period
target_start = pd.to_datetime('2007-06-01')
target_end = pd.to_datetime('2007-08-31')

# Baseline period
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')

# Range of files to fetch for baseline (including buffers)
fetch_start = baseline_start - pd.Timedelta(days=5)
fetch_end = baseline_end + pd.Timedelta(days=5)

def get_date_range(start, end):
    return pd.date_range(start, end)

target_dates = get_date_range(target_start, target_end)
baseline_fetch_dates = get_date_range(fetch_start, fetch_end)

def get_sst_for_region(date, region_bounds):
    date_str = date.strftime('%Y%m%d')
    remote_path = f'{path}/sst_{date_str}.nc'
    local_path = f'/work/sst_{date_str}.nc'
    try:
        fs.get(remote_path, local_path)
        with xr.open_dataset(local_path, engine='h5netcdf') as ds:
            # Subset to region
            subset = ds.analysed_sst.sel(
                latitude=slice(region_bounds[0], region_bounds[1]),
                longitude=slice(region_bounds[2], region_bounds[3])
            )
            # Convert to numpy and ensure float64
            data = subset.values.astype(np.float64)
            coords = {
                'lat': subset.latitude.values,
                'lon': subset.longitude.values,
                'time': subset.time.values
            }
            # Remove local file to save space
            os.remove(local_path)
            return data[0], coords
    except Exception as e:
        print(f"Error loading {date_str}: {e}")
        return None, None

# Get coordinates from the first target file
first_date = target_dates[0]
data_0, coords = get_sst_for_region(first_date, (lat_min, lat_max, lon_min, lon_max))

if data_0 is None:
    raise RuntimeError("Could not load the first target file.")

lats = coords['lat']
lons = coords['lon']
print(f"Region shape: {data_0.shape}")
print(f"Lats: {lats[0]} to {lats[-1]}")
print(f"Lons: {lons[0]} to {lons[-1]}")
