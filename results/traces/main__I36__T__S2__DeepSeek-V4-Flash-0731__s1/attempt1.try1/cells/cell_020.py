
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import fsspec
import xarray as xr

def day_of_year(month, day):
    month_start = {
        1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153,
        7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336,
    }
    return month_start[month] + day - 1

def dt_to_pydatetime(np_dt):
    return np_dt.astype('datetime64[us]').astype(datetime)

# Load data
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
times = ds.time.values

lat_idx = slice(330, 390)
lon_idx = slice(551, 611)

baseline_data = ds['analysed_sst'].isel(time=slice(3647, 7675),
                                         latitude=lat_idx, longitude=lon_idx).values
baseline_times = times[3647:7675]

target_data = ds['analysed_sst'].isel(time=slice(7821, 7913),
                                       latitude=lat_idx, longitude=lon_idx).values
target_times = times[7821:7913]

baseline_pydates = [dt_to_pydatetime(t) for t in baseline_times]
target_pydates = [dt_to_pydatetime(t) for t in target_times]

baseline_doy = np.array([day_of_year(d.month, d.day) for d in baseline_pydates])
target_doy = np.array([day_of_year(d.month, d.day) for d in target_pydates])

baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_in_range = np.array([(d >= baseline_start and d <= baseline_end) for d in baseline_pydates])

# Build pools
pool_indices = defaultdict(list)
for i, t0 in enumerate(baseline_pydates):
    if not baseline_in_range[i]:
        continue
    d = baseline_doy[i]
    if d == 60:
        continue
    t_start = t0 - timedelta(days=5)
    t_end = t0 + timedelta(days=5)
    for j, t in enumerate(baseline_pydates):
        if t_start <= t <= t_end:
            pool_indices[d].append(j)

for d in pool_indices:
    pool_indices[d] = sorted(set(pool_indices[d]))

# Sea cells
sea_mask = np.all(np.isfinite(target_data), axis=0)
n_lat, n_lon = sea_mask.shape

baseline_data_f64 = baseline_data.astype(np.float64)

# Compute raw threshold and climatology
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for d in pool_indices:
    if d == 60:
        continue
    idx = np.array(pool_indices[d])
    pool = baseline_data_f64[idx]
    for lat in range(n_lat):
        for lon in range(n_lon):
            if sea_mask[lat, lon]:
                vals = pool[:, lat, lon]
                valid = vals[np.isfinite(vals)]
                if len(valid) > 0:
                    threshold[d-1, lat, lon] = np.quantile(valid, 0.9, method='hazen')
                    climatology[d-1, lat, lon] = np.mean(valid)

# Day 60
for lat in range(n_lat):
    for lon in range(n_lon):
        if sea_mask[lat, lon]:
            threshold[59, lat, lon] = (threshold[58, lat, lon] + threshold[60, lat, lon]) / 2.0
            climatology[59, lat, lon] = (climatology[58, lat, lon] + climatology[60, lat, lon]) / 2.0

# Smoothing
def smooth_wrap(arr):
    n_days = 366
    result = np.zeros_like(arr)
    for lat in range(arr.shape[1]):
        for lon in range(arr.shape[2]):
            if np.isfinite(arr[0, lat, lon]):
                for d in range(n_days):
                    window = []
                    for k in range(-15, 16):
                        idx = (d + k) % n_days
                        if np.isfinite(arr[idx, lat, lon]):
                            window.append(arr[idx, lat, lon])
                    result[d, lat, lon] = np.mean(window)
    return result

smoothed_threshold = smooth_wrap(threshold)

# Determine hot days
n_target_days = len(target_pydates)
hot = np.zeros((n_target_days, n_lat, n_lon), dtype=bool)
target_data_f64 = target_data.astype(np.float64)

for t_idx in range(n_target_days):
    d = target_doy[t_idx]
    thresh = smoothed_threshold[d-1]
    hot[t_idx] = (target_data_f64[t_idx] >= thresh) & sea_mask

print("Hot days computed")

# Find per-cell MHWs
# For each sea cell, find runs of >= 5 consecutive hot days
# Join runs separated by 1-2 non-hot days

# Let's define the mhw mask: mhw[day, lat, lon] = 1 if cell is in an MHW on that day
mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

sea_cell_indices = np.argwhere(sea_mask)
print(f"Processing {len(sea_cell_indices)} sea cells")

for lat, lon in sea_cell_indices:
    hot_series = hot[:, lat, lon]
    
    # Find runs of hot days
    # A "run" means consecutive hot days
    # Then join runs separated by 1-2 non-hot days
    
    # Find all hot segments
    runs = []
    i = 0
    while i < n_target_days:
        if hot_series[i]:
            start = i
            while i < n_target_days and hot_series[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    if not runs:
        continue
    
    # Join runs separated by 1-2 non-hot days
    joined = []
    current = runs[0]
    for next_run in runs[1:]:
        gap = next_run[0] - current[1] - 1
        if 1 <= gap <= 2:
            # Join
            current = (current[0], next_run[1])
        else:
            joined.append(current)
            current = next_run
    joined.append(current)
    
    # Keep only runs of >= 5 days
    for start, end in joined:
        if end - start + 1 >= 5:
            mhw_mask[start:end+1, lat, lon] = 1

print(f"MHW cells on active days: {mhw_mask.sum()}")

# Regional events
# A day is active if at least one sea cell is in an MHW
active = np.any(mhw_mask > 0, axis=(1, 2))
print(f"Active days: {active.sum()}")

# Find maximal runs of consecutive active days
events = []
i = 0
while i < n_target_days:
    if active[i]:
        start = i
        while i < n_target_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
for start, end in events:
    onset = target_pydates[start].strftime('%Y-%m-%d')
    end_date = target_pydates[end].strftime('%Y-%m-%d')
    print(f"  Event: {onset} to {end_date}, duration {end-start+1} days")
