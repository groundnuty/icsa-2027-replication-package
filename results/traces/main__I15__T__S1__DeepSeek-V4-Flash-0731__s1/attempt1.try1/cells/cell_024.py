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

# Load data
baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

print(f"Baseline SST: {baseline_sst.shape}")
print(f"Target SST: {target_sst.shape}")

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

# Build date -> index lookup
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

for d in pools:
    pools[d] = sorted(pools[d])

# Verify pool sizes
for d in [1, 59, 61, 180, 365]:
    print(f"  doy {d}: {len(pools[d])} dates")

# Compute threshold and climatology for each doy and each cell
n_cells_lat = len(lat_idx)
n_cells_lon = len(lon_idx)
n_doy = 366

threshold = np.zeros((n_doy, n_cells_lat, n_cells_lon), dtype=np.float64)
climatology = np.zeros((n_doy, n_cells_lat, n_cells_lon), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    date_idxs = pools[d]
    pool_sst = baseline_sst[date_idxs, :, :]
    
    threshold[d-1, :, :] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
    climatology[d-1, :, :] = np.nanmean(pool_sst, axis=0)

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

# Smooth with 31-day moving mean wrapping around
smooth_threshold = np.zeros_like(threshold)
smooth_climatology = np.zeros_like(climatology)

for d in range(n_doy):
    idxs = [(d + k) % n_doy for k in range(-15, 16)]
    smooth_threshold[d, :, :] = np.mean(threshold[idxs, :, :], axis=0)
    smooth_climatology[d, :, :] = np.mean(climatology[idxs, :, :], axis=0)

print("\nSmoothed threshold range:", np.nanmin(smooth_threshold), "to", np.nanmax(smooth_threshold))
print("Smoothed climatology range:", np.nanmin(smooth_climatology), "to", np.nanmax(smooth_climatology))

# Determine sea cells
all_finite = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {np.sum(all_finite)} out of {n_cells_lat * n_cells_lon}")

# Target day-of-year
target_dates = []
for i in range(len(t_idx)):
    ts = t_vals[t_idx[i]]
    dt = datetime.utcfromtimestamp(ts.astype('datetime64[us]').astype(np.int64) / 1e6)
    target_dates.append(dt)

target_doy = [date_to_doy(dt.year, dt.month, dt.day) for dt in target_dates]

# Determine hot days
n_target = len(t_idx)
hot = np.zeros((n_target, n_cells_lat, n_cells_lon), dtype=bool)

for t in range(n_target):
    d = target_doy[t]
    hot[t, :, :] = (target_sst[t, :, :] >= smooth_threshold[d-1, :, :])

# Only sea cells can be hot
hot = hot & np.expand_dims(all_finite, axis=0)

print(f"Hot cell-days: {hot.sum()}")

# Per-cell MHWs
# Step 1: Find all maximal runs of consecutive hot days
# Step 2: Keep runs with length >= 5 as candidate MHWs
# Step 3: Join candidate MHWs separated by 1-2 non-hot days

mhw_mask = np.zeros((n_target, n_cells_lat, n_cells_lon), dtype=np.uint8)

for i in range(n_cells_lat):
    for j in range(n_cells_lon):
        if not all_finite[i, j]:
            continue
        
        hot_seq = hot[:, i, j].astype(int)
        
        # Find all maximal runs of consecutive hot days
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
        
        # Keep runs with length >= 5 as candidate MHWs
        candidate_mhws = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not candidate_mhws:
            continue
        
        # Join candidate MHWs separated by 1-2 non-hot days
        joined_mhws = [candidate_mhws[0]]
        for mhw in candidate_mhws[1:]:
            gap = mhw[0] - joined_mhws[-1][1] - 1
            if 1 <= gap <= 2:
                joined_mhws[-1] = (joined_mhws[-1][0], mhw[1])
            else:
                joined_mhws.append(mhw)
        
        # Mark MHW days
        for s, e in joined_mhws:
            mhw_mask[s:e+1, i, j] = 1

print(f"MHW cell-days: {mhw_mask.sum()}")

# Regional events
active = np.any(mhw_mask > 0, axis=(1, 2))

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
os.makedirs('output', exist_ok=True)

lat_region = ds.latitude.values[lat_idx]
lon_region = ds.longitude.values[lon_idx]
time_target = ds.time.values[t_idx]

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
