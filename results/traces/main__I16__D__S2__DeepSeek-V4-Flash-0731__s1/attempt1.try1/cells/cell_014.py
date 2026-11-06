
import xarray as xr
import numpy as np
from datetime import date, timedelta
from bisect import bisect_left, bisect_right
from collections import defaultdict

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

# Build list of baseline dates with doy
base_info = [(B, day_of_year(B.month, B.day)) for B in base_dates 
             if base_start_date <= B <= base_end_date]
base_date_list = [x[0] for x in base_info]

# Build D_to_pools
D_to_pools = {}
for i, D in enumerate(base_dates):
    lo = bisect_left(base_date_list, D - timedelta(days=5))
    hi = bisect_right(base_date_list, D + timedelta(days=5))
    pools = set()
    for j in range(lo, hi):
        pools.add(base_info[j][1])
    D_to_pools[i] = pools

# Now, for each doy d (1-366, d!=60), collect the time indices that contribute to pool d
doy_to_timeidx = defaultdict(list)
for i, pools in D_to_pools.items():
    for d in pools:
        if d != 60:
            doy_to_timeidx[d].append(i)

print("Number of doys with pools:", len(doy_to_timeidx))
print("Pool sizes per doy (sample):")
for d in [1, 59, 61, 100, 200, 300, 365, 366]:
    if d in doy_to_timeidx:
        print(f"  doy {d}: {len(doy_to_timeidx[d])} values")
