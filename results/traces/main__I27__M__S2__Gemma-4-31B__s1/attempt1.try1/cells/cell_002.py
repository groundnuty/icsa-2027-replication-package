import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Region and time constraints
LAT_MIN, LAT_MAX = 57.83, 59.03
LON_MIN, LON_MAX = 17.41, 18.61
TARGET_START = "2008-06-01"
TARGET_END = "2008-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

def get_doy(date):
    """Maps a date to a day of year from 1 to 366."""
    days_in_months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_months[:date.month - 1]) + date.day

# Load dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine="h5netcdf")

# Slice the region
# Using .sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX)) might not work if the coordinates are not sorted or if we need inclusive bounds.
# Let's check the coordinates.
print(f"Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}")

# Correct slicing for inclusive bounds
# We find indices for the boundaries.
lat_idx = np.where((ds.latitude.values >= LAT_MIN) & (ds.latitude.values <= LAT_MAX))[0]
lon_idx = np.where((ds.longitude.values >= LON_MIN) & (ds.longitude.values <= LON_MAX))[0]

# Use isel to slice. Assuming coordinates are sorted.
ds_region = ds.isel(latitude=slice(lat_idx[0], lat_idx[-1]+1), longitude=slice(lon_idx[0], lon_idx[-1]+1))
print(f"Region shape: {ds_region.analysed_sst.shape}")
