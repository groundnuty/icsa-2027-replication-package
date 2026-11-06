import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# Define region and periods
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87
baseline_start = pd.to_datetime("1992-01-01")
baseline_end = pd.to_datetime("2002-12-31")
target_start = pd.to_datetime("2008-06-01")
target_end = pd.to_datetime("2008-08-31")

# Windows for baseline
window_start = baseline_start - pd.Timedelta(days=5)
window_end = baseline_end + pd.Timedelta(days=5)

dataset_dir = "/data/icsa2027_data_20261101T090944Z/s1z"
all_files = os.listdir(dataset_dir)

def get_date_from_filename(filename):
    # filename is like 'sst_20231231.nc'
    date_str = filename.split('_')[1].split('.')[0]
    return pd.to_datetime(date_str, format='%Y%m%d')

# Filter files
baseline_files = []
target_files = []
for f in all_files:
    if f.startswith('sst_') and f.endswith('.nc'):
        dt = get_date_from_filename(f)
        if window_start <= dt <= window_end:
            baseline_files.append(f)
        if target_start <= dt <= target_end:
            target_files.append(f)

baseline_files.sort()
target_files.sort()

print(f"Baseline files: {len(baseline_files)}")
print(f"Target files: {len(target_files)}")

# Load data for the region
def load_region_sst(files):
    sst_list = []
    times = []
    lats = None
    lons = None
    
    for f in files:
        path = os.path.join(dataset_dir, f)
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            # Slice region
            subset = ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            sst_list.append(subset.values)
            times.append(ds.time.values[0])
            if lats is None:
                lats = ds.latitude.values
                lons = ds.longitude.values
                # Subset coords to match the sliced data
                lats = ds.latitude.values[(ds.latitude >= lat_min) & (ds.latitude <= lat_max)]
                lons = ds.longitude.values[(ds.longitude >= lon_min) & (ds.longitude <= lon_max)]
    
    # Re-slice the coordinates to be precise since slice() might include slightly more/less 
    # based on floating point or grid boundaries. Actually sel(slice) is inclusive and 
    # the values are fixed. Let's verify by reloading one.
    
    # For correctness, let's just use the subset's coordinates.
    # Wait, the above loop already did a slice. Let's do it better.
    return np.array(sst_list), np.array(times), lats, lons

# To avoid loading everything into memory at once if it's too much, 
# but 3600 cells * 4000 days * 8 bytes is ~115 MB. Should be fine.

# Re-do loading with precise slicing
def load_sst_precise(files):
    data = []
    times = []
    lat_coords = None
    lon_coords = None
    
    for f in files:
        path = os.path.join(dataset_dir, f)
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            # use .sel with slice is inclusive. 
            # Let's ensure we get exactly the same grid for every file.
            subset = ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            data.append(subset.values)
            times.append(ds.time.values[0])
            if lat_coords is None:
                lat_coords = subset.latitude.values
                lon_coords = subset.longitude.values
    
    return np.array(data, dtype=np.float64), np.array(times), lat_coords, lon_coords

# Load baseline and target
sst_baseline, times_baseline, lats, lons = load_sst_precise(baseline_files)
sst_target, times_target, _, _ = load_sst_precise(target_files)

print(f"SST baseline shape: {sst_baseline.shape}")
print(f"SST target shape: {sst_target.shape}")
