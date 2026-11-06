
import numpy as np
from datetime import date, timedelta
import xarray as xr
import os
import json

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# ============================================================
# 1. Load region coordinates
# ============================================================
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_idx = np.where((lat_all >= 57.85) & (lat_all <= 59.05))[0]
lon_idx = np.where((lon_all >= 21.01) & (lon_all <= 22.21))[0]
region_lat = lat_all[lat_idx]
region_lon = lon_all[lon_idx]
ds0.close()
nlat, nlon = len(lat_idx), len(lon_idx)

# ============================================================
# 2. Load target data (2013-06-01 to 2013-08-31)
# ============================================================
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
print(f"Target data: {n_target} days, shape {target_sst.shape}")

# Identify sea cells
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_mask.sum()}, non-sea: {(~sea_mask).sum()}")

# ============================================================
# 3. Load baseline data (1991-12-27 to 2003-01-05)
# ============================================================
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
print(f"Baseline data: {n_dates} days, shape {baseline_sst.shape}")

# ============================================================
# 4. Build pool dates for each doy
# ============================================================
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

# ============================================================
# 5. Compute threshold and climatology for each doy
# ============================================================
threshold = np.full((366, nlat, nlon), np.nan, dtype=np.float64)
climatology = np.full((366, nlat, nlon), np.nan, dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = pool_dates[doy]
    pool_data = baseline_sst[idxs]
    
    for ilat in range(nlat):
        for ilon in range(nlon):
            vals = pool_data[:, ilat, ilon]
            valid = vals[np.isfinite(vals)]
            if len(valid) > 0:
                threshold[doy-1, ilat, ilon] = np.percentile(valid, 90, method='hazen')
                climatology[doy-1, ilat, ilon] = np.mean(valid)

print("Computed threshold and climatology for doys 1-366 (except 60)")

# Check: all sea cells have valid values for all doys
sea_indices = np.where(sea_mask)
for ilat, ilon in zip(sea_indices[0], sea_indices[1]):
    if np.any(np.isnan(threshold[:, ilat, ilon])):
        print(f"Cell ({ilat},{ilon}) has NaN threshold!")
        break
else:
    print("All sea cells have valid threshold for all doys (except 60)")

# ============================================================
# 6. Set day 60 to mean of days 59 and 61
# ============================================================
valid_59 = np.isfinite(threshold[58])
valid_61 = np.isfinite(threshold[60])
both_valid = valid_59 & valid_61
threshold[59] = np.where(both_valid, (threshold[58] + threshold[60]) / 2.0, np.nan)
climatology[59] = np.where(both_valid, (climatology[58] + climatology[60]) / 2.0, np.nan)

print("Set day 60 threshold and climatology")

# ============================================================
# 7. Smooth with 31-day centered moving mean (wraparound)
# ============================================================
def smooth_31(a):
    """a: (366, nlat, nlon) array. Returns smoothed array."""
    n = 366
    result = np.full_like(a, np.nan)
    for i in range(n):
        # Average days i-15 to i+15 (mod 366)
        idxs = [(i + k) % n for k in range(-15, 16)]
        # For cells with NaN, the mean would be NaN. 
        # But for sea cells, all values should be valid.
        result[i] = np.nanmean(a[idxs], axis=0)
    return result

threshold_smooth = smooth_31(threshold)
climatology_smooth = smooth_31(climatology)

print("Smoothed threshold and climatology")

# Verify smoothing works
print("Threshold doy 153 before smooth:", threshold[152, 0, 0])
print("Threshold doy 153 after smooth:", threshold_smooth[152, 0, 0])
print("Climatology doy 153 before smooth:", climatology[152, 0, 0])
print("Climatology doy 153 after smooth:", climatology_smooth[152, 0, 0])

# Check that sea cells have valid smoothed values
for ilat, ilon in zip(sea_indices[0], sea_indices[1]):
    if np.any(np.isnan(threshold_smooth[:, ilat, ilon])):
        print(f"Cell ({ilat},{ilon}) has NaN smoothed threshold!")
        break
else:
    print("All sea cells have valid smoothed threshold for all doys")
