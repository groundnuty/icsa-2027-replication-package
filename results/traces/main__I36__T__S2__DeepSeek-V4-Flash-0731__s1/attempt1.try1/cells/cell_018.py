
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

baseline_doy = np.array([day_of_year(d.month, d.day) for d in baseline_pydates])

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
print(f"Sea cells: {sea_mask.sum()} out of {sea_mask.size}")

# Convert to float64
baseline_data_f64 = baseline_data.astype(np.float64)

# Compute raw threshold and climatology (index by doy-1)
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

# Vectorize the computation: for each doy, compute for all sea cells at once
sea_cell_mask_2d = sea_mask  # (n_lat, n_lon)

for d in pool_indices:
    if d == 60:
        continue
    idx = np.array(pool_indices[d])
    pool = baseline_data_f64[idx]  # (n_dates, n_lat, n_lon)
    
    # For each cell, compute threshold and climatology
    # This is slow in a loop, so let's vectorize where possible
    
    # Compute per-cell by iterating over cells but only sea cells
    for lat in range(n_lat):
        for lon in range(n_lon):
            if sea_cell_mask_2d[lat, lon]:
                vals = pool[:, lat, lon]
                valid = vals[np.isfinite(vals)]
                if len(valid) > 0:
                    threshold[d-1, lat, lon] = np.quantile(valid, 0.9, method='hazen')
                    climatology[d-1, lat, lon] = np.mean(valid)

# Set day 60 to mean of days 59 and 61
for lat in range(n_lat):
    for lon in range(n_lon):
        if sea_cell_mask_2d[lat, lon]:
            threshold[59, lat, lon] = (threshold[58, lat, lon] + threshold[60, lat, lon]) / 2.0
            climatology[59, lat, lon] = (climatology[58, lat, lon] + climatology[60, lat, lon]) / 2.0

print("Raw threshold and climatology computed")

# Smoothing
def smooth_wrap(arr):
    """Apply unweighted centred 31-day moving mean that wraps around.
    arr shape: (366, n_lat, n_lon)"""
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
smoothed_climatology = smooth_wrap(climatology)

print("Smoothing complete")

# Verify for first sea cell
sea_cell_indices = np.argwhere(sea_mask)
lat0, lon0 = sea_cell_indices[0]
print(f"First sea cell at ({lat0},{lon0})")
print(f"Smoothed threshold doy 153: {smoothed_threshold[152, lat0, lon0]}")
print(f"Smoothed climatology doy 153: {smoothed_climatology[152, lat0, lon0]}")
print(f"Raw threshold doy 153: {threshold[152, lat0, lon0]}")
print(f"Raw climatology doy 153: {climatology[152, lat0, lon0]}")
