
import numpy as np
from datetime import date, timedelta

def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Reconstruct from saved data - let me recompute in this cell
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

# For each time index i, the pools it belongs to
# Precompute for each date D: which doys are within ±5 days of a baseline date with that doy
# Simpler: for each doy d, find all dates D in baseline range such that D is within ±5 of a baseline date with doy=d

# Actually, let me precompute for each date D, which baseline dates B with |D-B|<=5 have doy values
# This is the D_to_pools approach

# But instead of looping over all 4018 baseline dates for each D (O(n^2)), let me be smarter
# For each D, only baseline dates within ±5 calendar days matter
# So I can slide a window

# Build list of (date, doy) for baseline dates
base_info = [(B, day_of_year(B.month, B.day)) for B in base_dates 
             if base_start_date <= B <= base_end_date]

# Build D_to_pools
D_to_pools = {}
from bisect import bisect_left, bisect_right
base_date_list = [x[0] for x in base_info]

for i, D in enumerate(base_dates):
    # Find baseline dates within ±5 days of D
    lo = bisect_left(base_date_list, D - timedelta(days=5))
    hi = bisect_right(base_date_list, D + timedelta(days=5))
    pools = set()
    for j in range(lo, hi):
        pools.add(base_info[j][1])
    D_to_pools[i] = pools

print("Done building D_to_pools")
print("Max pool size for any doy:", max(len(v) for v in D_to_pools.values()))
