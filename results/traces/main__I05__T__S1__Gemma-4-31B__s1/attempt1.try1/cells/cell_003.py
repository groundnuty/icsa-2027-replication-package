import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Region and periods
lat_min, lat_max = 54.39, 55.59
lon_min, lon_max = 18.25, 19.45
target_start = pd.to_datetime('2021-06-01')
target_end = pd.to_datetime('2021-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')

# Buffer for windows
buffer_start = baseline_start - timedelta(days=5)
buffer_end = baseline_end + timedelta(days=5)

def get_sst_for_period(start, end, lat_min, lat_max, lon_min, lon_max):
    # Generate date list
    date_range = pd.date_range(start, end)
    sst_list = []
    times = []
    
    # We need to find the files in the root_dir.
    # Files are named 'sst_YYYYMMDD.nc'
    for dt in date_range:
        filename = f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
        if filename in fs.ls(root_dir) or fs.exists(filename): # fs.ls is slow, but we can use fs.exists or similar
            # Actually fs.ls(root_dir) is already called once, let's just use the list
            pass
    
    # Let's optimize file loading
    return None

# Instead of calling fs.exists for every file, let's get the full list once.
all_files = fs.ls(root_dir)
all_files_set = set(all_files)

def load_sst_region(start, end, lat_min, lat_max, lon_min, lon_max):
    date_range = pd.date_range(start, end)
    sst_data = []
    actual_times = []
    
    for dt in date_range:
        filename = f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
        if filename in all_files_set:
            with fs.open(filename, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Slice region
                region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                sst_data.append(region_ds['analysed_sst'].values.squeeze())
                actual_times.append(dt)
    
    if not sst_data:
        return None, None
    
    sst_array = np.stack(sst_data, axis=0).astype(np.float64)
    return sst_array, actual_times

# To avoid memory issues, let's first load a sample to check the coordinate values
with fs.open(f'{root_dir}/sst_19820101.nc', "rb") as f:
    ds_sample = xr.open_dataset(f, engine="h5netcdf")
    lats = ds_sample.latitude.values
    lons = ds_sample.longitude.values

# Exact slice for coordinates
lat_mask = (lats >= lat_min) & (lats <= lat_max)
lon_mask = (lons >= lon_min) & (lons <= lon_max)
lats_region = lats[lat_mask]
lons_region = lons[lon_mask]

print(f"Lats region: {lats_region[0]} to {lats_region[-1]}, size {len(lats_region)}")
print(f"Lons region: {lons_region[0]} to {lons_region[-1]}, size {len(lons_region)}")
