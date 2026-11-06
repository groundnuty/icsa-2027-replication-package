
import os
import re
import numpy as np
from datetime import date, timedelta
import xarray as xr

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping (perpetual leap year)
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d.day + sum(month_days[:d.month])

# Region indices
sample = xr.open_dataset(os.path.join(base_dir, 'sst_20030601.nc'), engine='h5netcdf')
lat = sample.latitude.values
lon = sample.longitude.values
lat_idx = np.where((lat >= 60.09) & (lat <= 61.29))[0]
lon_idx = np.where((lon >= 20.01) & (lon <= 21.21))[0]
lat_region = lat[lat_idx]
lon_region = lon[lon_idx]
n_lat = len(lat_idx)
n_lon = len(lon_idx)
sample.close()
print(f"Region: {n_lat} x {n_lon} = {n_lat*n_lon} cells")

# Build list of all dates in baseline window (1991-12-27 to 2003-01-05)
baseline_dates = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    baseline_dates.append(d)
    d += timedelta(days=1)
print(f"Baseline window: {len(baseline_dates)} days")

# Check which dates are available
files = {}
for f in os.listdir(base_dir):
    m = re.match(r'sst_(\d{4})(\d{2})(\d{2})\.nc', f)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        files[d] = os.path.join(base_dir, f)

# Verify all baseline dates available
available = [d for d in baseline_dates if d in files]
print(f"Available baseline days: {len(available)}/{len(baseline_dates)}")

# Read all baseline data
# Store as dict: date -> (n_lat, n_lon) array
baseline_sst = {}
import time
start_time = time.time()
for i, d in enumerate(baseline_dates):
    if d in files:
        ds = xr.open_dataset(files[d], engine='h5netcdf')
        sst = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].astype(np.float64)
        baseline_sst[d] = sst
        ds.close()
    if (i+1) % 500 == 0:
        elapsed = time.time() - start_time
        print(f"Read {i+1}/{len(baseline_dates)} files, elapsed: {elapsed:.1f}s")
print(f"Done reading baseline. Total time: {time.time()-start_time:.1f}s")
print(f"Number of baseline days stored: {len(baseline_sst)}")
