
import fsspec
import xarray as xr
import numpy as np
import datetime
import time
import os

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Region
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Get region indices from a sample file
f = fs.open(f'{base}/sst_20120601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_idx_arr = np.where((lats >= lat_min) & (lats <= lat_max))[0]
lon_idx_arr = np.where((lons >= lon_min) & (lons <= lon_max))[0]
lat_idx = slice(lat_idx_arr[0], lat_idx_arr[-1]+1)
lon_idx = slice(lon_idx_arr[0], lon_idx_arr[-1]+1)
region_lats = lats[lat_idx]
region_lons = lons[lon_idx]
ds.close()
f.close()

print(f"Region: {len(lat_idx_arr)} lat x {len(lon_idx_arr)} lon")

# Build baseline date list
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += datetime.timedelta(days=1)

# Determine pool dates for each day of year
doy_to_pool_dates = {i: set() for i in range(1, 367)}
for date in baseline_dates:
    if 1992 <= date.year <= 2002:
        doy_val = doy_from_date(date)
        for offset in range(-5, 6):
            doy_to_pool_dates[doy_val].add(date + datetime.timedelta(days=offset))

# Read baseline data
print("Reading baseline data...")
start = time.time()
n_dates = len(baseline_dates)
baseline_sst = np.full((n_dates, len(lat_idx_arr), len(lon_idx_arr)), np.nan, dtype=np.float64)
date_to_idx = {}

for i, date in enumerate(baseline_dates):
    date_to_idx[date] = i
    fname = f'sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc'
    f = fs.open(f'{base}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst.values[0, lat_idx, lon_idx]
    ds.close()
    f.close()
    if (i+1) % 1000 == 0:
        print(f"  Read {i+1}/{n_dates}, elapsed: {time.time()-start:.1f}s")

print(f"Baseline read done in {time.time()-start:.1f}s")

# Save baseline data
os.makedirs('work', exist_ok=True)
np.save('work/baseline_sst.npy', baseline_sst)

# Also save the date list and index mapping
import pickle
with open('work/baseline_dates.pkl', 'wb') as f:
    pickle.dump(baseline_dates, f)
with open('work/date_to_idx.pkl', 'wb') as f:
    pickle.dump(date_to_idx, f)
with open('work/doy_to_pool_dates.pkl', 'wb') as f:
    # Convert to sets of date strings for pickling
    pickle.dump({k: sorted(v) for k, v in doy_to_pool_dates.items()}, f)

print("Saved baseline data to work/")
