import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import os
import json
from datetime import datetime, timedelta

# Configuration
root = 'icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 62.25, 63.45
lon_min, lon_max = 18.73, 19.93
baseline_start_date = pd.to_datetime('1991-12-27')
baseline_end_date = pd.to_datetime('2003-01-05')
target_start_date = pd.to_datetime('2012-06-01')
target_end_date = pd.to_datetime('2012-08-31')

fs = fsspec.filesystem('onedata')

def get_date_range(start, end):
    return pd.date_range(start, end)

baseline_dates = get_date_range(baseline_start_date, baseline_end_date)
target_dates = get_date_range(target_start_date, target_end_date)

all_needed_dates = sorted(list(baseline_dates) + list(target_dates))
needed_files = [f"sst_{d.strftime('%Y%m%d')}.nc" for d in all_needed_dates]

# Check if all needed files exist in the remote directory
all_files = fs.ls(root)
all_files_basenames = [os.path.basename(f) for f in all_files]
missing_files = [f for f in needed_files if f not in all_files_basenames]

print(f"Total needed files: {len(needed_files)}")
print(f"Missing files: {len(missing_files)}")
if missing_files:
    print(f"First 5 missing files: {missing_files[:5]}")

# Download files and process
# Since there are many files, we'll process them in batches or use a loop.
# To save space, we'll only load the region we need.

def load_region(remote_file):
    local_path = f"/work/{os.path.basename(remote_file)}"
    fs.get(remote_file, local_path)
    with xr.open_dataset(local_path, engine="h5netcdf") as ds:
        # Subset to region
        region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        # To avoid memory issues, convert to numpy and remove the local file immediately
        data = region_ds.analysed_sst.values.astype(np.float64)
        coords = {
            'lat': region_ds.latitude.values,
            'lon': region_ds.longitude.values,
            'time': region_ds.time.values
        }
    os.remove(local_path)
    return data, coords

# Instead of loading everything at once, let's be careful.
# Let's first find the coordinates using a single file.
sample_remote = f"{root}/{needed_files[0]}"
sample_local = "/work/sample_coords.nc"
fs.get(sample_remote, sample_local)
with xr.open_dataset(sample_local, engine="h5netcdf") as ds:
    lats = ds.latitude.values
    lons = ds.longitude.values
    lat_mask = (lats >= lat_min) & (lats <= lat_max)
    lon_mask = (lons >= lon_min) & (lons <= lon_max)
    # The coordinates are the same for all files.
    # Let's store the coordinates we'll use.
    final_lats = lats[lat_mask]
    final_lons = lons[lon_mask]
os.remove(sample_local)

print(f"Region shape: lat {len(final_lats)}, lon {len(final_lons)}")
