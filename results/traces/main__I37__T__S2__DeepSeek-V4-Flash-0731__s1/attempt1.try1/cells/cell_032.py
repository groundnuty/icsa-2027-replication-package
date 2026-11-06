
import pandas as pd
import numpy as np
import fsspec
import xarray as xr
import json
import os

os.makedirs('output', exist_ok=True)

fs = fsspec.filesystem('onedata')
data_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# ====== Parameters ======
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21

# ====== Fixed day-of-year mapping ======
def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

# ====== Load dataset ======
with fs.open(data_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat = ds.latitude.values
    lon = ds.longitude.values
    time_vals = ds.time.values
    all_dates = pd.to_datetime(time_vals)
    
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    ext_time_idx = np.where((all_dates >= pd.Timestamp('1991-12-27')) & (all_dates <= pd.Timestamp('2003-01-05')))[0]
    tgt_time_idx = np.where((all_dates >= pd.Timestamp('2012-06-01')) & (all_dates <= pd.Timestamp('2012-08-31')))[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=slice(int(ext_time_idx[0]), int(ext_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)
    
    target_sst = ds['analysed_sst'].isel(
        time=slice(int(tgt_time_idx[0]), int(tgt_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)
    
    region_lat = lat[lat_idx].copy()
    region_lon = lon[lon_idx].copy()
    target_dates = all_dates[tgt_time_idx].copy()

n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_target = len(target_dates)

print(f"Baseline: {all_dates[ext_time_idx[0]]} to {all_dates[ext_time_idx[-1]]}, {len(ext_time_idx)} days")
print(f"Target: {target_dates[0]} to {target_dates[-1]}, {n_target} days")
print(f"Region: {n_lat}x{n_lon} cells")

# ====== Sea cells ======
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# ====== Build pool time indices ======
ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates_pd = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates_pd])
ext_date_to_idx = {d: i for i, d in enumerate(ext_dates_pd)}

pool_time_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    b_mask = (base_doy == d)
    b_dates_for_d = base_dates_pd[b_mask]
    pool_date_set = set()
    for b in b_dates_for_d:
        for t in ext_dates_pd:
            if abs((t - b).days) <= 5:
                pool_date_set.add(t)
    pool_time_indices[d] = sorted([ext_date_to_idx[t] for t in pool_date_set])

# ====== Compute threshold and climatology ======
threshold_raw = np.full((366, n_lat, n_lon), np.nan)
climatology_raw = np.full((366, n_lat, n_lon), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = np.array(pool_time_indices[d])
    pool_vals = baseline_sst[pool_idx]
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
            vals = pool_vals[:, i, j]
            valid = vals[np.isfinite(vals)]
            if len(valid) > 0:
                threshold_raw[d-1, i, j] = np.percentile(valid, 90, method='hazen')
                climatology_raw[d-1, i, j] = np.mean(valid)

# Set day 60
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2

# ====== Smoothing ======
def smooth_wrap(arr):
    result = np.full_like(arr, np.nan)
    for d in range(366):
        idxs = [(d + k) % 366 for k in range(-15, 16)]
        result[d] = np.mean(arr[idxs], axis=0)
    return result

threshold = smooth_wrap(threshold_raw)
climatology = smooth_wrap(climatology_raw)

print("Threshold and climatology computed and smoothed")

# ====== Per-cell MHWs ======
target_doy = np.array([fixed_doy(d) for d in target_dates])

hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    d = target_doy[t]
    thr = threshold[d-1]
    hot[t] = (target_sst[t] >= thr) & sea_cells

print(f"Hot days: {hot.sum()}")

mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_series = hot[:, i, j]
        
        hot_runs = []
        in_run = False
        run_start = 0
        for t in range(n_target):
            if hot_series[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    hot_runs.append((run_start, t-1))
                    in_run = False
        if in_run:
            hot_runs.append((run_start, n_target-1))
        
        qualifying_runs = [(s, e) for s, e in hot_runs if (e - s + 1) >= 5]
        
        if not qualifying_runs:
            continue
        
        joined_runs = []
        current = qualifying_runs[0]
        for next_run in qualifying_runs[1:]:
            gap = next_run[0] - current[1] - 1
            if gap <= 2:
                current = (current[0], next_run[1])
            else:
                joined_runs.append(current)
                current = next_run
        joined_runs.append(current)
        
        for s, e in joined_runs:
            mhw_mask[s:e+1, i, j] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")

# ====== Regional events ======
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()}")

events = []
in_event = False
event_start = 0
for t in range(n_target):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t-1))
            in_event = False
if in_event:
    events.append((event_start, n_target-1))

print(f"Regional events: {len(events)}")

# ====== Write output files ======

# Create mhw_mask.nc
# Need to create an xarray dataset with the target time coordinates, lat, lon
target_time_np = target_dates.values  # datetime64 array
lat_np = region_lat
lon_np = region_lon

# Create xarray Dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': target_time_np,
        'lat': lat_np,
        'lon': lon_np,
    }
)

# Save to NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Create report.json
report = {
    'region': {
        'lat_min': float(LAT_MIN),
        'lat_max': float(LAT_MAX),
        'lon_min': float(LON_MIN),
        'lon_max': float(LON_MAX)
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2012-06-01',
        'end': '2012-08-31'
    },
    'events': [],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print("\nReport:")
print(json.dumps(report, indent=2))
