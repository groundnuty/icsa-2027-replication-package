
import xarray as xr
import numpy as np
from datetime import datetime, date, timedelta
from datetime import date as dt_date
from collections import defaultdict
import os

os.makedirs('output', exist_ok=True)

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
baseline_years = defaultdict(list)
d = dt_date(1992, 1, 1)
while d <= dt_date(2002, 12, 31):
    doy = day_of_year(d.month, d.day)
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

# Compute raw threshold and climatology
baseline_sst64 = baseline_sst.astype(np.float64)

threshold_raw = np.full((366, 60, 60), np.nan)
climatology_raw = np.full((366, 60, 60), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx = doy_to_pool_idx[doy]
    pool = baseline_sst64[idx]
    pool_sea = pool[:, sea_cells]
    q = np.nanquantile(pool_sea, 0.9, axis=0, method='hazen')
    m = np.nanmean(pool_sea, axis=0)
    threshold_raw[doy-1, sea_cells] = q
    climatology_raw[doy-1, sea_cells] = m

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2

# Correct smoothing: 31-day centred moving average wrapping around
def smooth_wrap_correct(arr):
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    result = np.zeros_like(arr)
    for i in range(366):
        result[i] = np.mean(padded[i:i+31], axis=0)
    return result

threshold_smooth = smooth_wrap_correct(threshold_raw)
climatology_smooth = smooth_wrap_correct(climatology_raw)

print("Smoothed threshold shape:", threshold_smooth.shape)
print("Smoothed climatology shape:", climatology_smooth.shape)
print("NaN in threshold:", np.isnan(threshold_smooth).sum())
print("NaN in climatology:", np.isnan(climatology_smooth).sum())

# Verify some values
print("Threshold sample (doy 153, idx 152, sea cell):")
# Find a sea cell
sea_idx = np.where(sea_cells)
si = sea_idx[0][0]
sj = sea_idx[1][0]
print(f"  Cell ({si},{sj}), sea_cells={sea_cells[si,sj]}")
print(f"  Threshold raw[152]: {threshold_raw[152, si, sj]}")
print(f"  Threshold smooth[152]: {threshold_smooth[152, si, sj]}")

# Save intermediate results
np.save('/tmp/threshold_smooth_correct.npy', threshold_smooth)
np.save('/tmp/climatology_smooth_correct.npy', climatology_smooth)
np.save('/tmp/sea_cells.npy', sea_cells)
np.save('/tmp/target_sst.npy', target_sst)
np.save('/tmp/target_time_idx.npy', target_time_idx)
np.save('/tmp/target_doy.npy', np.array([day_of_year(d.month, d.day) for d in 
    [datetime.utcfromtimestamp(int(t)/1e9).date() for t in time[target_time_idx]]]))

print("Saved corrected intermediate results")
