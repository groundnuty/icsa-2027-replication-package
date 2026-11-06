
import xarray as xr
import numpy as np
from datetime import date, timedelta
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
print("n_times:", n_times)

# Build date objects for each baseline time
base_dates = [date(1970,1,1) + timedelta(days=int((t - np.datetime64('1970-01-01')) / np.timedelta64(1,'D'))) 
              for t in base_times]
print("First/last:", base_dates[0], base_dates[-1])

# Baseline dates: 1992-01-01 to 2002-12-31
base_start_date = date(1992,1,1)
base_end_date = date(2002,12,31)

# For each baseline date, compute its doy
base_doy = {}
for B in base_dates:
    if base_start_date <= B <= base_end_date:
        base_doy[B] = day_of_year(B.month, B.day)

print("Number of baseline dates (1992-2002):", len(base_doy))

# For each time index i (date D), find pools it contributes to
# pools = set of doys d such that exists B in baseline with doy(B)=d and |D-B|<=5
D_to_pools = {}
for i, D in enumerate(base_dates):
    pools = set()
    for B, d in base_doy.items():
        if abs((D - B).days) <= 5:
            pools.add(d)
    D_to_pools[i] = pools

# Check a few
print("D 0 (1991-12-27) pools:", D_to_pools[0])
print("D 5 (1992-01-01) pools:", D_to_pools[5])
print("D 10 (1992-01-06) pools:", sorted(D_to_pools[10]))
