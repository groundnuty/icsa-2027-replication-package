import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89
target_start = '2010-06-01'
target_end = '2010-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    
    # Select region
    ds_region = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max)
    )
    
    # Select times: baseline and target
    # Baseline is 1992-2002, but windows go from 1991-12-27 to 2003-01-05
    # Let's be safe and slice a bit wider
    ds_baseline = ds_region.sel(time=slice('1991-12-20', '2003-01-10')).load()
    ds_target = ds_region.sel(time=slice(target_start, target_end)).load()

print(f"Baseline shape: {ds_baseline.analysed_sst.shape}")
print(f"Target shape: {ds_target.analysed_sst.shape}")
print(f"Latitude: {ds_region.latitude.values}")
print(f"Longitude: {ds_region.longitude.values}")
