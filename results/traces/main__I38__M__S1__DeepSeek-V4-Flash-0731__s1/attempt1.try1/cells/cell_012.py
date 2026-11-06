
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, time, json

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Day of year mapping
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# ===== STEP 0: Setup =====
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

# Region indices
ds = xr.open_dataset(f'{data_dir}/sst_19920101.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_idx = np.where((lats >= 60.49) & (lats <= 61.69))[0]
lon_idx = np.where((lons >= 17.25) & (lons <= 18.45))[0]
region_lats = lats[lat_idx]
region_lons = lons[lon_idx]
ds.close()

print(f"Region: {len(lat_idx)} lat x {len(lon_idx)} lon = {len(lat_idx)*len(lon_idx)} cells")

# ===== STEP 1: Load baseline data =====
# Map date to index
baseline_date_to_idx = {d: i for i, d in enumerate(all_baseline_dates)}

# Load baseline SST data for the region
# We'll load in batches to manage memory
baseline_sst = np.full((len(all_baseline_dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float32)

print("Loading baseline data...")
t0 = time.time()
for i, dt in enumerate(all_baseline_dates):
    fname = f'{data_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(fname, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{len(all_baseline_dates)} baseline files, elapsed: {time.time()-t0:.1f}s")

print(f"Baseline loaded in {time.time()-t0:.1f}s")

# ===== STEP 2: Load target data =====
target_sst = np.full((len(target_dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float32)
target_date_to_idx = {d: i for i, d in enumerate(target_dates)}

print("Loading target data...")
t0 = time.time()
for i, dt in enumerate(target_dates):
    fname = f'{data_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(fname, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()

print(f"Target loaded in {time.time()-t0:.1f}s")

# ===== STEP 3: Identify sea cells =====
# Sea cells: cells with finite SST on every day of target period
sea_cells = ~np.isnan(target_sst).all(axis=0)  # Cells with at least one valid
# Actually: cells whose SST is finite on EVERY day of the target period
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")
