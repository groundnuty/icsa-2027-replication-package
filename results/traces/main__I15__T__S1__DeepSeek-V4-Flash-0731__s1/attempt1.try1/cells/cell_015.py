import numpy as np
import xarray as xr
import fsspec
import json
import os
from datetime import datetime, timedelta

# Define doy mapping
def date_to_doy(year, month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

def doy_to_month_day(doy):
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

# Indices
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
b_idx = np.where((t_vals >= base_start) & (t_vals <= base_end))[0]

t_start = np.datetime64('2019-06-01')
t_end = np.datetime64('2019-08-31')
t_idx = np.where((t_vals >= t_start) & (t_vals <= t_end))[0]

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

# Load data
baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values
target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=lat_idx, longitude=lon_idx).values

print(f"Baseline SST: {baseline_sst.shape}, {baseline_sst.dtype}")
print(f"Target SST: {target_sst.shape}, {target_sst.dtype}")
print(f"Extended baseline dates: {t_vals[b_idx[0]]} to {t_vals[b_idx[-1]]}")
print(f"Target dates: {t_vals[t_idx[0]]} to {t_vals[t_idx[-1]]}")

# Convert to float64
baseline_sst = baseline_sst.astype(np.float64)
target_sst = target_sst.astype(np.float64)

# Build date objects for extended baseline
b_dates = []
for i in range(len(b_idx)):
    ts = t_vals[b_idx[i]]
    dt = datetime.utcfromtimestamp(ts.astype('datetime64[us]').astype(np.int64) / 1e6)
    b_dates.append(dt)

# Core baseline dates (1992-2002)
base_core_start = datetime(1992, 1, 1)
base_core_end = datetime(2002, 12, 31)
core_dates = []
for dt in b_dates:
    if base_core_start <= dt <= base_core_end:
        core_dates.append((dt, date_to_doy(dt.year, dt.month, dt.day)))

print(f"\nCore baseline dates: {len(core_dates)}")
print(f"First: {core_dates[0]}")
print(f"Last: {core_dates[-1]}")

# Check leap years in baseline
leap_years = [y for y in range(1992, 2003) if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)]
print(f"Leap years in baseline: {leap_years}")

# Build pool membership: for each doy d (1-366, d≠60), list of extended baseline date indices
# Efficient approach: for each core baseline date, mark all dates within ±5 days
# as belonging to that date's doy pool.

# First, let's build a lookup: date -> index in b_dates
date_to_idx = {}
for i, dt in enumerate(b_dates):
    date_to_idx[dt] = i

print(f"\nTotal extended baseline dates: {len(b_dates)}")
print(f"Total core baseline dates: {len(core_dates)}")
