
import xarray as xr
import numpy as np
from datetime import date, timedelta
from bisect import bisect_left, bisect_right
from collections import defaultdict
import pickle

def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]
time = ds.time.values
b_start = np.where(time >= np.datetime64('1991-12-27'))[0][0]
b_end = np.where(time <= np.datetime64('2003-01-05'))[0][-1]
baseline_region = ds['analysed_sst'].isel(time=slice(b_start, b_end+1), 
                                          latitude=lat_idx, longitude=lon_idx).load()

base_times = baseline_region.time.values
n_times = len(base_times)
base_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
              for t in base_times]

base_start_date = date(1992,1,1)
base_end_date = date(2002,12,31)
base_info = [(B, day_of_year(B.month, B.day)) for B in base_dates 
             if base_start_date <= B <= base_end_date]
base_date_list = [x[0] for x in base_info]

D_to_pools = {}
for i, D in enumerate(base_dates):
    lo = bisect_left(base_date_list, D - timedelta(days=5))
    hi = bisect_right(base_date_list, D + timedelta(days=5))
    pools = set()
    for j in range(lo, hi):
        pools.add(base_info[j][1])
    D_to_pools[i] = pools

doy_to_timeidx = defaultdict(list)
for i, pools in D_to_pools.items():
    for d in pools:
        if d != 60:
            doy_to_timeidx[d].append(i)

n_lat = len(lat_idx)
n_lon = len(lon_idx)
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

data = baseline_region.values.astype(np.float64)

for d, tidx in doy_to_timeidx.items():
    pool_data = data[tidx, :, :]
    threshold[d-1, :, :] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
    climatology[d-1, :, :] = np.nanmean(pool_data, axis=0)

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

print("Day 60 threshold sample:", threshold[59, :3, 0])
print("Day 59 threshold sample:", threshold[58, :3, 0])
print("Day 61 threshold sample:", threshold[60, :3, 0])

# Check NaNs
print("NaNs in threshold after day60 fix:", np.sum(np.isnan(threshold)))
print("NaNs in climatology after day60 fix:", np.sum(np.isnan(climatology)))

# Identify land cells (all NaN across all doys)
all_nan_cells = np.all(np.isnan(threshold), axis=0)
print("Land cells (all NaN):", np.sum(all_nan_cells), "out of", n_lat*n_lon)

# Save
np.save('/work/threshold_raw.npy', threshold)
np.save('/work/climatology_raw.npy', climatology)
