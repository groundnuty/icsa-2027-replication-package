
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Get lat/lon indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= 63.31) & (lat_vals <= 64.51))[0]
lon_indices = np.where((lon_vals >= 21.31) & (lon_vals <= 22.51))[0]

lat_slice = slice(lat_indices[0], lat_indices[-1]+1)
lon_slice = slice(lon_indices[0], lon_indices[-1]+1)

# Define day_of_year function
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

# Verify some values
print(f"Jan 1: {doy(1,1)}")
print(f"Feb 28: {doy(2,28)}")
print(f"Feb 29: {doy(2,29)}")
print(f"Mar 1: {doy(3,1)}")
print(f"Dec 31: {doy(12,31)}")

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

# Extended period for data access: 1991-12-27 to 2003-01-05
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')

# Generate all dates in the extended period
all_dates = pd.date_range(data_start, data_end, freq='D')
print(f"\nExtended period: {len(all_dates)} days from {all_dates[0]} to {all_dates[-1]}")

# For each day of year d, find pool dates
# Pool for d: all dates t in [data_start, data_end] such that exists baseline date t0 in [baseline_start, baseline_end]
# with doy(t0) = d and |t - t0| <= 5 days

# Generate all baseline dates
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')
print(f"Baseline period: {len(baseline_dates)} days")

# Create a mapping from date -> doy
# We need to handle that non-leap years have no day 60
def date_to_doy(dt):
    return doy(dt.month, dt.day)

# For each doy d (1-366, except 60), find pool dates
# First, for each doy d, find baseline dates with that doy
baseline_dates_by_doy = {}
for dt in baseline_dates:
    d = date_to_doy(dt)
    if d not in baseline_dates_by_doy:
        baseline_dates_by_doy[d] = []
    baseline_dates_by_doy[d].append(dt)

# Print summary for a few doys
for d in [1, 59, 60, 61, 366]:
    dates = baseline_dates_by_doy.get(d, [])
    print(f"DOY {d}: {len(dates)} baseline dates: {dates[:3]}...{dates[-3:] if len(dates)>3 else ''}")
