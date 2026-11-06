
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
    
    target_dates = all_dates[tgt_time_idx].copy()

n_lat, n_lon = 60, 60
sea_cells = ~np.isnan(target_sst).any(axis=0)

# Check cell (0,1) - compute raw threshold and climatology for all doys
i, j = 0, 1

ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates_pd = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates_pd])
ext_date_to_idx = {d: i for i, d in enumerate(ext_dates_pd)}

# Compute raw thresholds for all 366 doys for this cell
threshold_raw_cell = np.full(366, np.nan)
climatology_raw_cell = np.full(366, np.nan)

for d in range(1, 367):
    if d == 60:
        continue
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
    if len(valid) > 0:
        threshold_raw_cell[d-1] = np.percentile(valid, 90, method='hazen')
        climatology_raw_cell[d-1] = np.mean(valid)

# Set day 60
threshold_raw_cell[59] = (threshold_raw_cell[58] + threshold_raw_cell[60]) / 2
climatology_raw_cell[59] = (climatology_raw_cell[58] + climatology_raw_cell[60]) / 2

# Smooth
def smooth_wrap_1d(arr):
    result = np.full(366, np.nan)
    for d in range(366):
        idxs = [(d + k) % 366 for k in range(-15, 16)]
        result[d] = np.mean(arr[idxs])
    return result

threshold_smooth_cell = smooth_wrap_1d(threshold_raw_cell)
climatology_smooth_cell = smooth_wrap_1d(climatology_raw_cell)

# Compare with target
print(f"Target doys: {np.array([fixed_doy(d) for d in target_dates])}")
print(f"\nFor cell ({i},{j}):")
print(f"{'doy':>5} {'date':>12} {'target':>10} {'thr_raw':>10} {'thr_smooth':>12} {'clm_smooth':>12} {'hot':>5}")
for t in range(0, 92, 10):
    d = fixed_doy(target_dates[t])
    date_str = str(target_dates[t].date())
    print(f"{d:>5} {date_str:>12} {target_sst[t,i,j]:>10.4f} {threshold_raw_cell[d-1]:>10.4f} {threshold_smooth_cell[d-1]:>12.4f} {climatology_smooth_cell[d-1]:>12.4f} {target_sst[t,i,j] >= threshold_smooth_cell[d-1]}")
