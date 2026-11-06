
import fsspec
import xarray as xr
import numpy as np
import datetime
import os
import json

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Region
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37

# Get region indices
f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat_all = ds.latitude.values
lon_all = ds.longitude.values
lat_idx = np.where((lat_all >= lat_min) & (lat_all <= lat_max))[0]
lon_idx = np.where((lon_all >= lon_min) & (lon_all <= lon_max))[0]
lat_min_i, lat_max_i = lat_idx.min(), lat_idx.max()
lon_min_i, lon_max_i = lon_idx.min(), lon_idx.max()
region_lat = lat_all[lat_min_i:lat_max_i+1]
region_lon = lon_all[lon_min_i:lon_max_i+1]
print(f"Region: lat {region_lat[0]} to {region_lat[-1]}, lon {region_lon[0]} to {region_lon[-1]}")
print(f"Grid: {len(region_lat)} x {len(region_lon)}")
ds.close()

# Define date range and day_of_year function
def day_of_year(d):
    doy = (d - datetime.date(d.year, 1, 1)).days + 1
    is_leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    if not is_leap and d.month >= 3:
        doy += 1
    return doy

# Load all baseline data
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

all_dates = []
d = baseline_start
while d <= baseline_end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

n_baseline = len(all_dates)
print(f"Loading {n_baseline} baseline files...")

# Load baseline data
baseline_data = np.zeros((n_baseline, 60, 60), dtype=np.float32)
baseline_doy = np.zeros(n_baseline, dtype=np.int32)

import time
t0 = time.time()
for i, date in enumerate(all_dates):
    fpath = f'{base}/sst_{date.strftime("%Y%m%d")}.nc'
    f = fs.open(fpath, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    baseline_data[i] = ds.analysed_sst.values[0, lat_min_i:lat_max_i+1, lon_min_i:lon_max_i+1]
    ds.close()
    f.close()
    baseline_doy[i] = day_of_year(date)
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{n_baseline} ({time.time()-t0:.1f}s)")

print(f"Baseline data loaded in {time.time()-t0:.1f}s")
print(f"Baseline data shape: {baseline_data.shape}")
print(f"NaN count: {np.isnan(baseline_data).sum()}")
