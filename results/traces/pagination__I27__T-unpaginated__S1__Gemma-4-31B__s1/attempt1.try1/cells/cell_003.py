import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'
all_files = fs.ls(base_path)

# Date ranges
baseline_start = pd.Timestamp('1991-12-27')
baseline_end = pd.Timestamp('2003-01-05')
target_start = pd.Timestamp('2008-06-01')
target_end = pd.Timestamp('2008-08-31')

def get_date_from_filename(filename):
    # filename like 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
    date_str = filename.split('/')[-1].split('_')[1].split('.')[0]
    return pd.Timestamp(date_str)

baseline_files = []
target_files = []

for f in all_files:
    dt = get_date_from_filename(f)
    if baseline_start <= dt <= baseline_end:
        baseline_files.append(f)
    if target_start <= dt <= target_end:
        target_files.append(f)

baseline_files.sort()
target_files.sort()

print(f"Baseline files: {len(baseline_files)}")
print(f"Target files: {len(target_files)}")

# Region bounds
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

def load_region(files):
    datasets = []
    for f in files:
        with fs.open(f, "rb") as site_g:
            ds = xr.open_dataset(site_g, engine="h5netcdf")
            # Select region
            ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            datasets.append(ds_reg)
    return xr.concat(datasets, dim='time')

# To save memory, we might want to load and process baseline and target separately.
# But the region is small, so we should be fine.
# Let's check the region size.
with fs.open(baseline_files[0], "rb") as site_g:
    ds_sample = xr.open_dataset(site_g, engine="h5netcdf")
    lat_slice = ds_sample.latitude.sel(latitude=slice(lat_min, lat_max))
    lon_slice = ds_sample.longitude.sel(longitude=slice(lon_min, lon_max))
    print(f"Region size: {len(lat_slice)} x {len(lon_slice)}")
