import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
import json

def get_sst_file_path(date):
    return f'/data/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'

def load_sst_region(date, lat_min, lat_max, lon_min, lon_max):
    path = get_sst_file_path(date)
    try:
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            # Slice the region
            region_ds = ds.sel(
                latitude=slice(lat_min, lat_max),
                longitude=slice(lon_min, lon_max)
            )
            # Ensure inclusive bounds if sel doesn't handle it perfectly for floats
            # Actually slice is inclusive for the coordinate values if they exist.
            # Let's be explicit just in case.
            return region_ds.analysed_sst.values.astype(np.float64)
    except FileNotFoundError:
        return None

# Parameters
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
target_start = datetime(2014, 6, 1)
target_end = datetime(2014, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# 1. Find sea cells
target_dates = pd.date_range(target_start, target_end)
sst_target_list = []
for d in target_dates:
    val = load_sst_region(d, lat_min, lat_max, lon_min, lon_max)
    if val is None:
        # This is a problem. We need all days for sea cell definition.
        # Let's check if all files exist first.
        print(f"Missing file for {d.date()}")
    sst_target_list.append(val)

# Convert to 3D array (time, lat, lon)
sst_target = np.stack(sst_target_list)
# Sea cells: SST is finite on every day of the target period
sea_mask = np.all(np.isfinite(sst_target), axis=0)
print(f"Sea cells found: {np.sum(sea_mask)}")
print(f"Target shape: {sst_target.shape}")
