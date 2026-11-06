
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, time

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# Build pool dates for each doy
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

doy_to_baseline_dates = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for b in doy_to_baseline_dates.get(doy, []):
        for i in range(-5, 6):
            pool_dates.add(b + timedelta(days=i))
    doy_to_pool_dates[doy] = sorted(pool_dates)

# All unique baseline dates needed
all_baseline_dates = sorted(set().union(*doy_to_pool_dates.values()))

# Target dates
target_start = date(2003, 6, 1)
target_end = date(2003, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Baseline dates: {len(all_baseline_dates)}")
print(f"Target dates: {len(target_dates)}")

# Load baseline data
# First, let's check the lat/lon indices
ds = xr.open_dataset(f'{data_dir}/sst_19920101.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_sel = slice(60.49, 61.69)  # inclusive
lon_sel = slice(17.25, 18.45)

lat_idx = np.where((lats >= 60.49) & (lats <= 61.69))[0]
lon_idx = np.where((lons >= 17.25) & (lons <= 18.45))[0]
print(f"Lat idx: {lat_idx[0]}-{lat_idx[-1]}, count={len(lat_idx)}")
print(f"Lon idx: {lon_idx[0]}-{lon_idx[-1]}, count={len(lon_idx)}")
ds.close()
