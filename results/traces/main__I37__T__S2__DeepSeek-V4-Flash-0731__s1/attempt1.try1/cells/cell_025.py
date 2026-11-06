
import pandas as pd
import numpy as np
import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')
data_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21

def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

with fs.open(data_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values
    lon = ds.longitude.values
    time_vals = ds.time.values
    all_dates = pd.to_datetime(time_vals)
    
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    ext_time_idx = np.where((all_dates >= pd.Timestamp('1991-12-27')) & (all_dates <= pd.Timestamp('2003-01-05')))[0]
    tgt_time_idx = np.where((all_dates >= pd.Timestamp('2012-06-01')) & (all_dates <= pd.Timestamp('2012-08-31')))[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=slice(int(ext_time_idx[0]), int(ext_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)
    
    target_sst = ds['analysed_sst'].isel(
        time=slice(int(tgt_time_idx[0]), int(tgt_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)

n_lat, n_lon = 60, 60
sea_cells = ~np.isnan(target_sst).any(axis=0)

# Check: for a sea cell, compare target SST to smoothed threshold
# First check cell (0,1)
i, j = 0, 1
print(f"Cell ({i},{j}), sea: {sea_cells[i,j]}")
print(f"Target SST: {target_sst[:, i, j]}")
print(f"Min target SST: {np.nanmin(target_sst[:, i, j])}")
print(f"Max target SST: {np.nanmax(target_sst[:, i, j])}")

# Check what threshold should be for doy 153-244
# doy 153 = Jun 1, doy 244 = Aug 31
# The raw threshold for this cell at various doys
print("\nLet me compute thresholds for this cell")

# Build pools
ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates_pd = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates_pd])
ext_date_to_idx = {d: i for i, d in enumerate(ext_dates_pd)}

# For doy 153 (Jun 1)
d = 153
b_mask = (base_doy == d)
b_dates_for_d = base_dates_pd[b_mask]
pool_date_set = set()
for b in b_dates_for_d:
    for t in ext_dates_pd:
        if abs((t - b).days) <= 5:
            pool_date_set.add(t)
pool_dates = sorted(pool_date_set)
pool_idx = [ext_date_to_idx[t] for t in pool_dates]
pool_vals = baseline_sst[pool_idx, i, j]
valid = pool_vals[~np.isnan(pool_vals)]
print(f"doy {d}: pool has {len(valid)} valid values")
print(f"  threshold (hazen 90th): {np.percentile(valid, 90, method='hazen'):.4f}")
print(f"  climatology: {np.mean(valid):.4f}")
print(f"  target SST on Jun 1: {target_sst[0, i, j]:.4f}")

# Check a few more doys
for d in [170, 180, 190, 200, 210, 220, 230, 244]:
    b_mask = (base_doy == d)
    b_dates_for_d = base_dates_pd[b_mask]
    pool_date_set = set()
    for b in b_dates_for_d:
        for t in ext_dates_pd:
            if abs((t - b).days) <= 5:
                pool_date_set.add(t)
    pool_dates = sorted(pool_date_set)
    pool_idx = [ext_date_to_idx[t] for t in pool_dates]
    pool_vals = baseline_sst[pool_idx, i, j]
    valid = pool_vals[~np.isnan(pool_vals)]
    
    # Find which target day corresponds to this doy
    tgt_doy = np.array([fixed_doy(dt) for dt in pd.to_datetime(target_dates)])
    # This doesn't work since target_dates not in scope. Let me compute
    # doy 153 = Jun 1, so doy 170 = Jun 18, etc.
    # Just compare with the target SST for the corresponding day
    
    thr = np.percentile(valid, 90, method='hazen')
    clm = np.mean(valid)
    
    # Target day index for this doy
    target_day_idx = d - 153  # since doy 153 is target day 0
    if 0 <= target_day_idx < 92:
        print(f"doy {d}: thr={thr:.4f}, clm={clm:.4f}, target_SST={target_sst[target_day_idx, i, j]:.4f}, hot={target_sst[target_day_idx, i, j] >= thr}")
    else:
        print(f"doy {d}: thr={thr:.4f}, clm={clm:.4f}")
