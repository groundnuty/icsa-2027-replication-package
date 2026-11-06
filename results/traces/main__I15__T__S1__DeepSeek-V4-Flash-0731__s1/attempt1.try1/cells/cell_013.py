import numpy as np
import xarray as xr
import fsspec
import json
import os
from datetime import datetime, timedelta

# Define the doy mapping functions
def date_to_doy(year, month, day):
    """Fixed mapping by month and day."""
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

def doy_to_month_day(doy):
    """Convert doy (1-366) to (month, day). Fixed mapping."""
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
    for m in range(12):
        if doy <= cum_days[m+1]:
            return m+1, doy - cum_days[m]
    raise ValueError(f"Invalid doy: {doy}")

# Load data
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

t_vals = ds.time.values

# Extended baseline range: 1991-12-27 to 2003-01-05
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
b_idx = np.where((t_vals >= base_start) & (t_vals <= base_end))[0]

# Target range
t_start = np.datetime64('2019-06-01')
t_end = np.datetime64('2019-08-31')
t_idx = np.where((t_vals >= t_start) & (t_vals <= t_end))[0]

# Region
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

print(f"Extended baseline: {len(b_idx)} days, {t_vals[b_idx[0]]} to {t_vals[b_idx[-1]]}")
print(f"Target: {len(t_idx)} days, {t_vals[t_idx[0]]} to {t_vals[t_idx[-1]]}")
print(f"Region: {len(lat_idx)} lat x {len(lon_idx)} lon")

# Load baseline data for region
baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values
print(f"Baseline SST shape: {baseline_sst.shape}, dtype: {baseline_sst.dtype}")

# Load target data for region
target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=lat_idx, longitude=lon_idx).values
print(f"Target SST shape: {target_sst.shape}, dtype: {target_sst.dtype}")
