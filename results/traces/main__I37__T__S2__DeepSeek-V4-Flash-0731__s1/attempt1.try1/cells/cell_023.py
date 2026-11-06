
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
    
    ext_start = pd.Timestamp('1991-12-27')
    ext_end = pd.Timestamp('2003-01-05')
    ext_time_idx = np.where((all_dates >= ext_start) & (all_dates <= ext_end))[0]
    
    tgt_start = pd.Timestamp('2012-06-01')
    tgt_end = pd.Timestamp('2012-08-31')
    tgt_time_idx = np.where((all_dates >= tgt_start) & (all_dates <= tgt_end))[0]
    
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

# Check cell (0,1)
i, j = 0, 1
ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')

# Check what pool day 153 (Jun 1) looks like for this cell
# doy 153 = Jun 1 (since Jan=31, Feb=29, Mar=31, Apr=30, May=31 => 31+29+31+30+31=152, so Jun 1 = 153)
print(f"doy 153 corresponds to Jun 1")
print(f"Target SST on Jun 1 2012: {target_sst[0, i, j]}")

# Find the pool for doy 153
base_dates_pd = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates_pd])
b_mask = (base_doy == 153)
b_dates = base_dates_pd[b_mask]
print(f"Baseline dates with doy 153: {b_dates}")

# Get pool dates
pool_dates = set()
for b in b_dates:
    for t in ext_dates_pd:
        if abs((t - b).days) <= 5:
            pool_dates.add(t)
pool_dates = sorted(pool_dates)
print(f"Pool has {len(pool_dates)} dates")

# Get values for this cell
ext_date_to_idx = {d: i for i, d in enumerate(ext_dates_pd)}
pool_idx = [ext_date_to_idx[t] for t in pool_dates]
pool_vals = baseline_sst[pool_idx, i, j]
valid = pool_vals[~np.isnan(pool_vals)]
print(f"Pool values (valid count={len(valid)}):")
print(valid)
print(f"90th percentile (Hazen): {np.percentile(valid, 90, method='hazen'):.4f}")
print(f"Mean: {np.mean(valid):.4f}")
