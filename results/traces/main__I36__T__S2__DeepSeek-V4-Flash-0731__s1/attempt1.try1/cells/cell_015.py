
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

# Arrays indexed by doy-1 (0-365) for doy 1-366
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

# Compute for each doy
for d in pool_indices:
    if d == 60:
        continue
    idx = np.array(pool_indices[d])
    pool = baseline_data_f64[idx]  # shape (n_dates, n_lat, n_lon)
    
    # Compute per cell
    for lat in range(n_lat):
        for lon in range(n_lon):
            if sea_mask[lat, lon]:
                vals = pool[:, lat, lon]
                valid = vals[np.isfinite(vals)]
                if len(valid) > 0:
                    threshold[d-1, lat, lon] = np.quantile(valid, 0.9, method='hazen')
                    climatology[d-1, lat, lon] = np.mean(valid)

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
for lat in range(n_lat):
    for lon in range(n_lon):
        if sea_mask[lat, lon]:
            threshold[59, lat, lon] = (threshold[58, lat, lon] + threshold[60, lat, lon]) / 2.0
            climatology[59, lat, lon] = (climatology[58, lat, lon] + climatology[60, lat, lon]) / 2.0

print("Threshold shape:", threshold.shape)
# Check some values
print(f"Threshold for doy 153 (Jun 1), cell [0,0]: {threshold[152, 0, 0]}")
print(f"Climatology for doy 153, cell [0,0]: {climatology[152, 0, 0]}")
# Check non-NaN counts
print(f"Non-NaN thresholds: {np.sum(np.isfinite(threshold))}")
print(f"Non-NaN climatologies: {np.sum(np.isfinite(climatology))}")
