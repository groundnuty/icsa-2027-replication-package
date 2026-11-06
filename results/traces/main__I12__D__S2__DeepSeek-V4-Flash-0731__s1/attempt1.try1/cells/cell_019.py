
import numpy as np
import pandas as pd
import xarray as xr
import json
import os

# Reload everything
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Baseline window
mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]

# Target period
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]

base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Step 1: Sea cells
n_lat, n_lon = 60, 60
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

print(f"Sea cells: {sea_cells.sum()}")

# Day of year mapping
def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build pools
full_base_time = base_time
base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

n_doy = 366
pool_indices = {}

for d in range(1, n_doy + 1):
    if d == 60:
        continue
    bd_mask = (base_doys == d)
    bd_dates = base_dates[bd_mask]
    
    if len(bd_dates) == 0:
        pool_indices[d] = np.array([], dtype=int)
        continue
    
    pool_date_set = set()
    for B in bd_dates:
        for delta in range(-5, 6):
            pool_date_set.add(B + pd.Timedelta(days=delta))
    
    indices = np.array([i for i, t in enumerate(full_base_time) if t in pool_date_set], dtype=int)
    pool_indices[d] = indices

# Compute threshold and climatology
threshold = np.full((n_doy + 1, n_lat, n_lon), np.nan)
climatology = np.full((n_doy + 1, n_lat, n_lon), np.nan)

for d in range(1, n_doy + 1):
    if d == 60:
        continue
    idx = pool_indices[d]
    if len(idx) == 0:
        continue
    pool = base_sst[idx]
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
            vals = pool[:, i, j]
            valid = vals[np.isfinite(vals)]
            if len(valid) == 0:
                continue
            threshold[d, i, j] = np.quantile(valid, 0.9, method='hazen')
            climatology[d, i, j] = np.mean(valid)

# Set day 60 as mean of days 59 and 61
threshold[60] = (threshold[59] + threshold[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0

# Smoothing
def smooth_31day(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean that wraps around."""
    result = np.zeros_like(arr)
    for d in range(366):
        result[d] = np.mean(arr[(np.arange(d-15, d+16) % 366)])
    return result

thresh_smoothed = np.full_like(threshold, np.nan)
clim_smoothed = np.full_like(climatology, np.nan)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        t_arr = threshold[1:367, i, j]
        c_arr = climatology[1:367, i, j]
        thresh_smoothed[1:367, i, j] = smooth_31day(t_arr)
        clim_smoothed[1:367, i, j] = smooth_31day(c_arr)

# Step 3: Per-cell MHWs
n_target = len(idx_target)
target_doys = np.array([date_to_doy(t) for t in target_time])

# Hot days
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        for t_idx in range(n_target):
            d = target_doys[t_idx]
            sst_val = target_sst[t_idx, i, j]
            if np.isfinite(sst_val) and sst_val >= thresh_smoothed[d, i, j]:
                hot[t_idx, i, j] = True

# Per-cell MHWs
# 1. Find runs of >=5 consecutive hot days
# 2. Join MHWs separated by 1-2 non-hot days

per_cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        h = hot[:, i, j]
        
        # Find all runs of consecutive hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target):
            if h[t]:
                if not in_run:
                    in_run = True
                    run_start = t
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_target - 1))
        
        # Keep only runs of >=5 hot days (initial MHWs)
        mhws = [(s, e) for (s, e) in runs if (e - s + 1) >= 5]
        
        # Join MHWs separated by 1-2 non-hot days
        if len(mhws) == 0:
            continue
        
        joined = []
        current = mhws[0]
        for m in mhws[1:]:
            gap = m[0] - current[1] - 1
            if gap <= 2:
                current = (current[0], m[1])
            else:
                joined.append(current)
                current = m
        joined.append(current)
        
        # Mark the joined MHW days
        for (s, e) in joined:
            per_cell_mhw[s:e+1, i, j] = True

# Step 4: Regional events
active = np.zeros(n_target, dtype=bool)
for t in range(n_target):
    active[t] = np.any(per_cell_mhw[t])

print("Active days:", active.sum())

events = []
in_event = False
event_start = 0
for t in range(n_target):
    if active[t]:
        if not in_event:
            in_event = True
            event_start = t
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_target - 1))

print("Regional events:", len(events))
for (s, e) in events:
    print(f"  Event: {target_time[s].strftime('%Y-%m-%d')} to {target_time[e].strftime('%Y-%m-%d')}")

# Write output
os.makedirs('output', exist_ok=True)

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]
target_time_np = ds.time.values[idx_target]

mhw_data = per_cell_mhw.astype(np.uint8)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'latitude', 'longitude'), mhw_data)
    },
    coords={
        'time': target_time_np,
        'latitude': region_lat,
        'longitude': region_lon,
    }
)

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("\nWrote output/mhw_mask.nc")

report = {
    'region': {
        'lat_min': 56.09,
        'lat_max': 57.29,
        'lon_min': 10.55,
        'lon_max': 11.75
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2009-06-01',
        'end': '2009-08-31'
    },
    'events': [
        {'onset': target_time[s].strftime('%Y-%m-%d'), 'end': target_time[e].strftime('%Y-%m-%d')}
        for (s, e) in events
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print("\nDone!")
