
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
sea_flat = sea_cells.ravel()

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
    doy_to_pool_idx[doy] = np.array(idx_list)

# Compute threshold and climatology for each doy
# baseline_sst shape: (4028, 60, 60)
baseline_sst64 = baseline_sst.astype(np.float64)

threshold = np.full((366, 60, 60), np.nan)
climatology = np.full((366, 60, 60), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx = doy_to_pool_idx[doy]
    pool = baseline_sst64[idx]  # (121, 60, 60)
    
    # For sea cells, compute percentile and mean
    # Reshape to (121, n_sea)
    pool_sea = pool[:, sea_cells]  # (121, 3303)
    
    # Compute 90th percentile per column ignoring NaN
    # Use nanquantile with method='hazen'
    q = np.nanquantile(pool_sea, 0.9, axis=0, method='hazen')
    m = np.nanmean(pool_sea, axis=0)
    
    threshold[doy, sea_cells] = q
    climatology[doy, sea_cells] = m

print("Computed per-day thresholds and climatology")
print("Threshold non-NaN count:", np.sum(~np.isnan(threshold)))
print("Climatology non-NaN count:", np.sum(~np.isnan(climatology)))
print("Expected (sea cells * 365):", 3303 * 365)

# Set day 60 to mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2  # 0-indexed: 59 is doy 60
climatology[59] = (climatology[58] + climatology[60]) / 2

print("After day 60 fill:")
print("Threshold non-NaN count:", np.sum(~np.isnan(threshold)))
print("Climatology non-NaN count:", np.sum(~np.isnan(climatology)))
print("Expected:", 3303 * 366)
