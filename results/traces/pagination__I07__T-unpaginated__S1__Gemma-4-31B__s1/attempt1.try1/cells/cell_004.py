import numpy as np
import pandas as pd
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import json

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start = pd.Timestamp('2021-06-01')
target_end = pd.Timestamp('2021-08-31')

def get_sst_subset(date):
    date_str = date.strftime('%Y%m%d')
    path = f'{base_path}/sst_{date_str}.nc'
    try:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            # We need to ensure we get the correct slice. 
            # Let's use .sel with method='nearest' if needed, but the range is inclusive.
            # The coordinates are likely monotonic.
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            )
            return subset.values.astype(np.float64), ds.latitude.values, ds.longitude.values
    except Exception as e:
        return None, None, None

# 1. Sea Cells
target_dates = pd.date_range(target_start, target_end)
sst_target_list = []
lats, lons = None, None

for date in target_dates:
    sst, la, lo = get_sst_subset(date)
    if sst is None:
        # If any day is missing, we can't determine sea cells properly?
        # But the task says "SST is finite on every day". 
        # If a file is missing, it's not finite.
        sst_target_list.append(np.full((60, 60), np.nan)) 
    else:
        sst_target_list.append(sst)
        if lats is None:
            # we only need the subset of lats/lons for the output
            # But get_sst_subset returns the full arrays.
            # Let's fix get_sst_subset to return the sliced coordinates.
            pass

# Wait, I need the sliced coordinates for the mask.
def get_sst_subset_fixed(date):
    date_str = date.strftime('%Y%m%d')
    path = f'{base_path}/sst_{date_str}.nc'
    try:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            subset_ds = ds.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            )
            return subset_ds.analysed_sst.values.astype(np.float64), subset_ds.latitude.values, subset_ds.longitude.values
    except Exception as e:
        return None, None, None

# Redo target data collection
sst_target_list = []
sliced_lats, sliced_lons = None, None
for date in target_dates:
    sst, la, lo = get_sst_subset_fixed(date)
    if sst is None:
        # Handle missing file by adding NaNs
        if sliced_lats is not None:
            sst_target_list.append(np.full((len(sliced_lats), len(sliced_lons)), np.nan))
        else:
            # This is tricky. We need to know the shape.
            # Let's find one valid file first.
            sst_target_list.append(None)
    else:
        sst_target_list.append(sst)
        sliced_lats, sliced_lons = la, lo

# Find the shape if we encountered NaNs at the start
if None in sst_target_list:
    # Replace None with NaNs using the discovered shape
    shape = (len(sliced_lats), len(sliced_lons))
    sst_target_list = [sst if sst is not None else np.full(shape, np.nan) for sst in sst_target_list]

sst_target = np.stack(sst_target_list) # (time, lat, lon)
# Sea cells: SST is finite on every day of the target period
# np.isfinite(sst_target).all(axis=0)
sea_mask = np.all(np.isfinite(sst_target), axis=0)
print(f"Sea cells found: {np.sum(sea_mask)} out of {sea_mask.size}")
