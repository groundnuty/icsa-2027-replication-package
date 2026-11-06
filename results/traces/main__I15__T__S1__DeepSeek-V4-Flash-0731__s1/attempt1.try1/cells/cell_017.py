import numpy as np
import xarray as xr
import fsspec
import json
import os
from datetime import datetime, timedelta

# Define doy mapping
def date_to_doy(year, month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Load data
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

t_vals = ds.time.values

# Indices
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
b_idx = np.where((t_vals >= base_start) & (t_vals <= base_end))[0]

t_start = np.datetime64('2019-06-01')
t_end = np.datetime64('2019-08-31')
t_idx = np.where((t_vals >= t_start) & (t_vals <= t_end))[0]

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

# Load data (chunk to avoid memory issues)
baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

print(f"Baseline SST: {baseline_sst.shape}, {baseline_sst.dtype}")
print(f"Target SST: {target_sst.shape}, {target_sst.dtype}")

# Build date objects for extended baseline
b_dates = []
for i in range(len(b_idx)):
    ts = t_vals[b_idx[i]]
    dt = datetime.utcfromtimestamp(ts.astype('datetime64[us]').astype(np.int64) / 1e6)
    b_dates.append(dt)

# Core baseline dates (1992-2002)
base_core_start = datetime(1992, 1, 1)
base_core_end = datetime(2002, 12, 31)
core_dates = []
for dt in b_dates:
    if base_core_start <= dt <= base_core_end:
        core_dates.append((dt, date_to_doy(dt.year, dt.month, dt.day)))

print(f"Core baseline dates: {len(core_dates)}")

# Build date -> index lookup for extended baseline
date_to_idx = {}
for i, dt in enumerate(b_dates):
    date_to_idx[dt] = i

# Build pools for each doy (1-366, d≠60)
pools = {d: set() for d in range(1, 367) if d != 60}

for b_dt, b_doy in core_dates:
    if b_doy == 60:
        continue
    
    for delta in range(-5, 6):
        t = b_dt + timedelta(days=delta)
        if t in date_to_idx:
            pools[b_doy].add(date_to_idx[t])

# Convert sets to sorted lists
for d in pools:
    pools[d] = sorted(pools[d])

print("Pool sizes:")
for d in [1, 59, 61, 180, 365]:
    print(f"  doy {d}: {len(pools[d])}")

# Now compute threshold and climatology for each doy and each cell
n_cells_lat = len(lat_idx)
n_cells_lon = len(lon_idx)
n_doy = 366

# Initialize arrays (using float64)
threshold = np.zeros((n_doy, n_cells_lat, n_cells_lon), dtype=np.float64)
climatology = np.zeros((n_doy, n_cells_lat, n_cells_lon), dtype=np.float64)

# For each doy, compute threshold and climatology
for d in range(1, 367):
    if d == 60:
        continue
    
    date_idxs = pools[d]
    if len(date_idxs) == 0:
        print(f"WARNING: doy {d} has empty pool")
        continue
    
    # Extract SST values for this doy pool
    pool_sst = baseline_sst[date_idxs, :, :]  # (n_dates, n_lat, n_lon)
    
    # Compute 90th percentile (Hazen method) ignoring NaN
    # numpy's percentile with method='hazen' is Hyndman-Fan type 5
    # which matches MATLAB's quantile default
    threshold[d-1, :, :] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
    
    # Compute mean ignoring NaN
    climatology[d-1, :, :] = np.nanmean(pool_sst, axis=0)

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

print("\nThreshold and climatology computed")
print(f"Threshold shape: {threshold.shape}")
print(f"Threshold range: {np.nanmin(threshold):.2f} to {np.nanmax(threshold):.2f}")
print(f"Climatology range: {np.nanmin(climatology):.2f} to {np.nanmax(climatology):.2f}")

# Smooth with 31-day moving mean wrapping around
# Day d averages days d-15 to d+15 (mod 366)
smooth_threshold = np.zeros_like(threshold)
smooth_climatology = np.zeros_like(climatology)

for d in range(n_doy):
    # Indices d-15 to d+15 (mod 366)
    idxs = [(d + k) % n_doy for k in range(-15, 16)]
    # Average over these day-of-year indices for each cell
    smooth_threshold[d, :, :] = np.mean(threshold[idxs, :, :], axis=0)
    smooth_climatology[d, :, :] = np.mean(climatology[idxs, :, :], axis=0)

print("\nSmoothed threshold and climatology computed")
print(f"Smoothed threshold range: {np.nanmin(smooth_threshold):.2f} to {np.nanmax(smooth_threshold):.2f}")
print(f"Smoothed climatology range: {np.nanmin(smooth_climatology):.2f} to {np.nanmax(smooth_climatology):.2f}")

# Now determine sea cells: finite SST on every day of target period
target_dates = []
for i in range(len(t_idx)):
    ts = t_vals[t_idx[i]]
    dt = datetime.utcfromtimestamp(ts.astype('datetime64[us]').astype(np.int64) / 1e6)
    target_dates.append(dt)

# Sea cells: finite SST on every target day
# target_sst shape: (n_target_days, n_lat, n_lon)
all_finite = np.all(np.isfinite(target_sst), axis=0)  # (n_lat, n_lon)
print(f"\nSea cells: {np.sum(all_finite)} out of {n_cells_lat * n_cells_lon}")

# Determine day-of-year for each target date
target_doy = [date_to_doy(dt.year, dt.month, dt.day) for dt in target_dates]
print(f"Target doys: {target_doy[:5]}...{target_doy[-5:]}")

# Determine per-cell MHW
# For each sea cell, check if each target day is hot
# A day is hot if SST >= threshold[doy] for that cell
n_target = len(t_idx)
hot = np.zeros((n_target, n_cells_lat, n_cells_lon), dtype=bool)

for t in range(n_target):
    d = target_doy[t]
    # threshold[d-1] is for doy d
    hot[t, :, :] = (target_sst[t, :, :] >= smooth_threshold[d-1, :, :])

print(f"\nHot days per cell: min={hot.sum(axis=0).min()}, max={hot.sum(axis=0).max()}")
print(f"Total hot cell-days: {hot.sum()}")

# Per-cell MHWs: runs of >=5 consecutive hot days, join gaps of 1-2 non-hot days
# First, set land cells to never hot
hot = hot & np.expand_dims(all_finite, axis=0)  # Only sea cells can be hot

# For each cell, find per-cell MHWs
# Initialize mhw mask: 1 where cell is inside a per-cell MHW
mhw_mask = np.zeros((n_target, n_cells_lat, n_cells_lon), dtype=np.uint8)

for i in range(n_cells_lat):
    for j in range(n_cells_lon):
        if not all_finite[i, j]:
            continue  # Land cell, no MHW
        
        # Get hot sequence for this cell
        hot_seq = hot[:, i, j].astype(int)
        
        # Find runs of hot days
        # First, mark hot days
        # Then join runs separated by 1-2 non-hot days
        # A per-cell MHW starts as a run of >=5 consecutive hot days
        # Runs separated by 1-2 non-hot days are joined
        
        # Find all hot runs (maximal consecutive runs of hot days)
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target):
            if hot_seq[t] == 1 and not in_run:
                in_run = True
                run_start = t
            elif hot_seq[t] == 0 and in_run:
                in_run = False
                runs.append((run_start, t-1))
        if in_run:
            runs.append((run_start, n_target-1))
        
        if not runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = [runs[0]]
        for r in runs[1:]:
            gap = r[0] - joined_runs[-1][1] - 1
            if 1 <= gap <= 2:
                # Join
                joined_runs[-1] = (joined_runs[-1][0], r[1])
            else:
                joined_runs.append(r)
        
        # Keep only runs of length >= 5
        valid_runs = [(s, e) for s, e in joined_runs if (e - s + 1) >= 5]
        
        # Mark MHW days
        for s, e in valid_runs:
            mhw_mask[s:e+1, i, j] = 1

print(f"\nMHW cell-days: {mhw_mask.sum()}")

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw_mask > 0, axis=(1, 2))  # (n_target,)

# Regional MHW event = maximal run of consecutive active days
events = []
in_event = False
event_start = 0
for t in range(n_target):
    if active[t] and not in_event:
        in_event = True
        event_start = t
    elif not active[t] and in_event:
        in_event = False
        events.append((event_start, t-1))
if in_event:
    events.append((event_start, n_target-1))

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')}")

# Save results
print("\nSaving results...")
os.makedirs('output', exist_ok=True)

# Create mhw_mask.nc
# Need to write with dimensions (time, lat, lon) using dataset coordinate values
# Use the actual lat/lon values from the dataset and target dates

lat_region = ds.latitude.values[lat_idx]
lon_region = ds.longitude.values[lon_idx]
time_target = ds.time.values[t_idx]

print(f"lat_region: {lat_region[:3]}...{lat_region[-3:]}, count={len(lat_region)}")
print(f"lon_region: {lon_region[:3]}...{lon_region[-3:]}, count={len(lon_region)}")
print(f"time_target: {time_target[0]} to {time_target[-1]}, count={len(time_target)}")
print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"all_finite shape: {all_finite.shape}")

# Write the NetCDF file
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_target,
        'lat': lat_region,
        'lon': lon_region,
    }
)
ds_out['mhw'].attrs['units'] = '1'
ds_out['mhw'].attrs['description'] = '1 where cell is inside a per-cell MHW on that day'
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved mhw_mask.nc")

# Write report.json
region = {
    "lat_min": 56.13,
    "lat_max": 57.33,
    "lon_min": 17.71,
    "lon_max": 18.91
}

report = {
    "region": region,
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2019-06-01",
        "end": "2019-08-31"
    },
    "events": [
        {"onset": target_dates[s].strftime('%Y-%m-%d'), "end": target_dates[e].strftime('%Y-%m-%d')}
        for s, e in events
    ],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as fjson:
    json.dump(report, fjson, indent=2)

print("\nSaved report.json")
print(json.dumps(report, indent=2))
