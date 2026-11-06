
import numpy as np
import xarray as xr
import json
import os
import warnings
from datetime import date, timedelta

warnings.filterwarnings('ignore')

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# ====== Region setup ======
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_idx = np.where((lat_all >= 57.85) & (lat_all <= 59.05))[0]
lon_idx = np.where((lon_all >= 21.01) & (lon_all <= 22.21))[0]
region_lat = lat_all[lat_idx]
region_lon = lon_all[lon_idx]
ds0.close()
nlat, nlon = len(lat_idx), len(lon_idx)
print(f"Region: {nlat} lats x {nlon} lons")

# ====== Load target data ======
target_start = date(2013, 6, 1)
target_end = date(2013, 8, 31)
target_dates = []
target_sst = []
d = target_start
while d <= target_end:
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    target_sst.append(ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].astype(np.float64))
    target_dates.append(d)
    ds.close()
    d += timedelta(days=1)
target_sst = np.array(target_sst)
n_target = len(target_dates)
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Target: {n_target} days, sea cells: {sea_mask.sum()}")

# ====== Load baseline data ======
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
n_dates = len(all_dates)
date_to_idx = {d: i for i, d in enumerate(all_dates)}
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

baseline_sst = np.zeros((n_dates, nlat, nlon), dtype=np.float64)
for i, d in enumerate(all_dates):
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    baseline_sst[i] = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()
print(f"Baseline: {n_dates} days loaded, shape {baseline_sst.shape}")

# ====== Build pools ======
pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool = []
    for D in baseline_1992_2002:
        if doy_of_date(D) == doy:
            for k in range(-5, 6):
                X = D + timedelta(days=k)
                if X in date_to_idx:
                    pool.append(date_to_idx[X])
    pool_dates[doy] = np.array(pool)
print("Pools built")

# ====== Compute threshold and climatology ======
threshold = np.full((366, nlat, nlon), np.nan, dtype=np.float64)
climatology = np.full((366, nlat, nlon), np.nan, dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_data = baseline_sst[pool_dates[doy]]
    threshold[doy-1] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
    climatology[doy-1] = np.nanmean(pool_data, axis=0)

# Set day 60 to mean of days 59 and 61
valid_59 = np.isfinite(threshold[58])
valid_61 = np.isfinite(threshold[60])
both_valid = valid_59 & valid_61
threshold[59] = np.where(both_valid, (threshold[58] + threshold[60]) / 2.0, np.nan)
climatology[59] = np.where(both_valid, (climatology[58] + climatology[60]) / 2.0, np.nan)
print("Threshold and climatology computed")

# Save intermediate results
np.save('/tmp/threshold.npy', threshold)
np.save('/tmp/climatology.npy', climatology)
np.save('/tmp/region_lat.npy', region_lat)
np.save('/tmp/region_lon.npy', region_lon)
np.save('/tmp/sea_mask.npy', sea_mask)
np.save('/tmp/target_dates_str.npy', np.array([d.strftime('%Y-%m-%d') for d in target_dates]))
np.save('/tmp/target_sst.npy', target_sst)
print("Intermediate results saved")

# Sanity checks
print("Threshold at doy 153 (Jun 1), cell (0,0):", threshold[152, 0, 0])
print("Climatology at doy 153 (Jun 1), cell (0,0):", climatology[152, 0, 0])
print("NaN count in threshold:", np.sum(np.isnan(threshold)))
print("NaN count in climatology:", np.sum(np.isnan(climatology)))
