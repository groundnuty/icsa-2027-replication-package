
import xarray as xr
import numpy as np
import pandas as pd
import json
import os

# Load the dataset to get coordinate values
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

# Get region coordinates from dataset
region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
region_lats = region.latitude.values
region_lons = region.longitude.values

# Target times
target_sel = region.sel(time=slice('2004-06-01', '2004-08-31'))
target_times = target_sel.time.values

print("Region lat:", region_lats[:3], "...", region_lats[-3:], "count:", len(region_lats))
print("Region lon:", region_lons[:3], "...", region_lons[-3:], "count:", len(region_lons))
print("Target times:", target_times[0], "to", target_times[-1], "count:", len(target_times))

# Load MHW mask
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60)
print("MHW mask shape:", mhw_mask.shape)

# Verify dimensions match
print("mhw_mask[0].shape:", mhw_mask[0].shape, "expected:", (len(region_lats), len(region_lons)))
