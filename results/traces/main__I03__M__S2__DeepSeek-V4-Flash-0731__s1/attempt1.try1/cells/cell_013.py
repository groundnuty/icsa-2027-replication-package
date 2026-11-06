
import xarray as xr
import numpy as np
from datetime import datetime, date, timedelta
from datetime import date as dt_date
from collections import defaultdict

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))

time = ds['time'].values

# Load target data
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_sst = ds['analysed_sst'].isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values

# Load baseline data
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time >= baseline_start) & (time <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]
baseline_sst = ds['analysed_sst'].isel(time=baseline_time_idx, latitude=lat_idx, longitude=lon_idx).values

# Sea cells
sea_cells = ~np.isnan(target_sst).any(axis=0)
print("Sea cells:", sea_cells.sum())

# Day of year function
def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

# Baseline dates as Python date objects
baseline_dates = []
for i in baseline_time_idx:
    t = time[i]
    dt = datetime.utcfromtimestamp(int(t) / 1e9)
    baseline_dates.append(dt.date())

# Generate baseline year dates grouped by doy
baseline_years = {}
d = dt_date(1992, 1, 1)
while d <= dt_date(2002, 12, 31):
    doy = day_of_year(d.month, d.day)
    if doy not in baseline_years:
        baseline_years[doy] = []
    baseline_years[doy].append(d)
    d += timedelta(days=1)

# For each doy d, find which baseline indices are in its pool
doy_to_pool_idx = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates_set = set()
    for y in baseline_years[doy]:
        for i in range(-5, 6):
            pool_dates_set.add(y + timedelta(days=i))
    
    idx_list = []
    for i, bd in enumerate(baseline_dates):
        if bd in pool_dates_set:
            idx_list.append(i)
    doy_to_pool_idx[doy] = idx_list

print("doy 1 pool size:", len(doy_to_pool_idx[1]))
print("doy 59 pool size:", len(doy_to_pool_idx[59]))
print("doy 61 pool size:", len(doy_to_pool_idx[61]))
print("doy 366 pool size:", len(doy_to_pool_idx[366]))
