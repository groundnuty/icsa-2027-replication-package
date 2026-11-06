import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region bounds
lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45

# Target period
target_start = '2010-06-01'
target_end = '2010-08-31'

# Baseline period
baseline_start_date = pd.Timestamp('1992-01-01')
baseline_end_date = pd.Timestamp('2002-12-31')

# Buffer for windows
baseline_data_start = '1991-12-27'
baseline_data_end = '2003-01-05'

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    
    # Slice region
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Load target period
    sst_target = ds_region.sel(time=slice(target_start, target_end)).analysed_sst.load()
    
    # Load baseline period (including buffers)
    sst_baseline = ds_region.sel(time=slice(baseline_data_start, baseline_data_end)).analysed_sst.load()

# Convert to float64 for calculations
sst_target = sst_target.astype(np.float64)
sst_baseline = sst_baseline.astype(np.float64)

# Coordinates for output
times = sst_target.time.values
lats = sst_target.latitude.values
lons = sst_target.longitude.values

print(f"Target shape: {sst_target.shape}")
print(f"Baseline shape: {sst_baseline.shape}")
