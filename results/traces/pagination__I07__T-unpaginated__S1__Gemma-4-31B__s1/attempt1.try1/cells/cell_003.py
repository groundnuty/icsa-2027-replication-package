import numpy as np
import pandas as pd
import xarray as xr
import fsspec
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Region bounds
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25

# Target period
target_start = pd.Timestamp('2021-06-01')
target_end = pd.Timestamp('2021-08-31')

# Baseline period
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
# Windows extend +/- 5 days
baseline_data_start = baseline_start - pd.Timedelta(days=5)
baseline_data_end = baseline_end + pd.Timedelta(days=5)

def get_sst_for_date(date):
    date_str = date.strftime('%Y%m%d')
    path = f'{base_path}/sst_{date_str}.nc'
    try:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            # Subset region
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            )
            return subset.values, ds.latitude.values, ds.longitude.values
    except Exception as e:
        return None, None, None

# Check data availability and get coordinates
test_date = target_start
sst, lats, lons = get_sst_for_date(test_date)
if sst is not None:
    print(f"Success! SST shape: {sst.shape}, Lats: {lats.shape}, Lons: {lons.shape}")
    print(f"Lats range: {lats[0]}, {lats[-1]}")
    print(f"Lons range: {lons[0]}, {lons[-1]}")
else:
    print("Failed to load data.")
