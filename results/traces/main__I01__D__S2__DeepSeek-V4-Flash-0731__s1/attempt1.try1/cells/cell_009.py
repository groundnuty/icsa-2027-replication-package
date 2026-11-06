
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import json

# ========== Build day-of-year pools (date indices per doy) ==========
days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_date(dt):
    return days_before_month[dt.month - 1] + dt.day

# We need the base_sst and base_dates from the previous cell
# Let me re-load everything since state doesn't persist

import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]

base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
t_idx_base = np.where((ds.time.values >= base_start) & (ds.time.values <= base_end))[0]
base_dates = ds.time.values[t_idx_base]
base_sst = ds.analysed_sst.isel(time=t_idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_dates = ds.time.values[t_idx_tgt]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

base_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in base_dates]
tgt_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in tgt_dates]

# Sea cells
n_tgt = len(tgt_dates_py)
sea_cells = np.all(~np.isnan(tgt_sst), axis=0)

# Determine which date indices belong to each doy pool
baseline_date_indices = [i for i, d in enumerate(base_dates_py) 
                         if datetime(1992,1,1) <= d <= datetime(2002,12,31)]
baseline_doy = {i: doy_from_date(base_dates_py[i]) for i in baseline_date_indices}

from collections import defaultdict
date_to_pools = defaultdict(list)
for i in range(len(base_dates_py)):
    t = base_dates_py[i]
    for j in baseline_date_indices:
        b = base_dates_py[j]
        if abs((t - b).days) <= 5:
            d = baseline_doy[j]
            if d != 60:
                date_to_pools[i].append(d)

# Invert: doy -> list of date indices
doy_to_dates = defaultdict(list)
for i, pools in date_to_pools.items():
    for d in pools:
        doy_to_dates[d].append(i)

print("Doy coverage:", len(doy_to_dates))
# Check each doy has some dates
missing = set(range(1,367)) - set(doy_to_dates.keys()) - {60}
print("Missing doys:", missing)

# Check sizes of pools
for d in [1, 59, 61, 153, 244, 366]:
    print(f"doy {d}: {len(doy_to_dates[d])} dates")

# ========== Compute threshold and climatology per sea cell ==========
# For each doy d and sea cell, pool = base_sst[dates_in_doy_pool, lat, lon]
# threshold = 90th percentile (Hazen method) of pool, ignoring NaN
# climatology = mean of pool, ignoring NaN

n_sea = sea_cells.sum()
sea_lat_idx, sea_lon_idx = np.where(sea_cells)

# Pre-compute for efficiency
n_doy = 366
threshold = np.full((n_doy, 60, 60), np.nan)
climatology = np.full((n_doy, 60, 60), np.nan)

for d in range(1, n_doy+1):
    if d == 60:
        continue
    dates_in_pool = doy_to_dates[d]
    if len(dates_in_pool) == 0:
        continue
    # Extract SST for these dates for all cells
    pool_vals = base_sst[dates_in_pool, :, :]  # shape (n_pool_dates, 60, 60)
    
    # For each cell, compute threshold and climatology
    for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
        vals = pool_vals[:, li, lo]
        valid = ~np.isnan(vals)
        if valid.sum() == 0:
            continue
        threshold[d, li, lo] = np.quantile(vals[valid], 0.9, method='hazen')
        climatology[d, li, lo] = np.mean(vals[valid])

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = np.nanmean(np.stack([threshold[58, :, :], threshold[60, :, :]]), axis=0)
climatology[59, :, :] = np.nanmean(np.stack([climatology[58, :, :], climatology[60, :, :]]), axis=0)

print("Threshold computed for all days")
print("Sample threshold values (cell 0):", threshold[58, sea_lat_idx[0], sea_lon_idx[0]], 
      threshold[59, sea_lat_idx[0], sea_lon_idx[0]], 
      threshold[60, sea_lat_idx[0], sea_lon_idx[0]])
