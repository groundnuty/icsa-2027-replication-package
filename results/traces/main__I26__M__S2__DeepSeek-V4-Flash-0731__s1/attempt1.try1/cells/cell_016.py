
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
import time

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Setup
start = date(1991, 12, 27)
end = date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
all_dates = np.array(all_dates, dtype=object)
n_dates = len(all_dates)

base_start_d = date(1992, 1, 1)
base_end_d = date(2002, 12, 31)
base_mask = np.array([base_start_d <= x <= base_end_d for x in all_dates])
date_to_idx = {d: i for i, d in enumerate(all_dates)}

doy_to_base_dates = defaultdict(list)
for y in all_dates[base_mask]:
    d = day_of_year_custom(y)
    doy_to_base_dates[d].append(y)

doy_to_pool_mask = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_mask = np.zeros(n_dates, dtype=bool)
    for y in doy_to_base_dates[d]:
        y_idx = date_to_idx[y]
        lo = max(0, y_idx - 5)
        hi = min(n_dates, y_idx + 6)
        pool_mask[lo:hi] = True
    doy_to_pool_mask[d] = pool_mask

# Load data
import xarray as xr
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_idx = slice(217, 277)
lon_idx = slice(421, 481)
base_start_idx = 3647
base_end_idx = 7674
tgt_start_idx = 9282
tgt_end_idx = 9373

base_sub = ds.analysed_sst.isel(time=slice(base_start_idx, base_end_idx+1),
                                 latitude=lat_idx, longitude=lon_idx)
base_data = base_sub.values

tgt_sub = ds.analysed_sst.isel(time=slice(tgt_start_idx, tgt_end_idx+1),
                                latitude=lat_idx, longitude=lon_idx)
tgt_data = tgt_sub.values
ds.close()

# Target time
time_all = pd.DatetimeIndex(xr.open_dataset(path, engine='h5netcdf').time.values)
tgt_time = time_all[tgt_start_idx:tgt_end_idx+1]

# Get lat/lon coordinates
ds2 = xr.open_dataset(path, engine='h5netcdf')
lat_vals = ds2.latitude.values[217:277]
lon_vals = ds2.longitude.values[421:481]
ds2.close()

print(f"Target time range: {tgt_time[0]} to {tgt_time[-1]}, {len(tgt_time)} days")
print(f"Target time: {[str(t.date()) for t in tgt_time[:3]]}")

# Sea cells
sea_cells = ~np.isnan(tgt_data).any(axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Load saved thresholds and climatology
threshold = np.load('/tmp/threshold_smoothed.npy')  # (366, 60, 60)
climatology = np.load('/tmp/climatology_smoothed.npy')

print(f"Threshold shape: {threshold.shape}")
print(f"Climatology shape: {climatology.shape}")

# Now detect per-cell MHWs
# Target period: 2007-06-01 to 2007-08-31, 92 days

# Compute day of year for each target day
tgt_doy = np.array([day_of_year_custom(pd.Timestamp(t).date()) for t in tgt_time])
print(f"Target doy: {tgt_doy[:5]} ... {tgt_doy[-5:]}")

# For each sea cell, determine hot days
# A day is hot if SST >= threshold[doy-1]
n_tgt = len(tgt_time)
n_lat, n_lon = 60, 60

# Initialize hot mask: (n_tgt, n_lat, n_lon)
hot = np.zeros((n_tgt, n_lat, n_lon), dtype=bool)

for t in range(n_tgt):
    doy = tgt_doy[t]
    hot[t] = tgt_data[t] >= threshold[doy-1]

print(f"Hot days computed. Total hot cell-days: {hot.sum()}")

# Now find per-cell MHWs
# A per-cell MHW is a run of at least 5 consecutive hot days
# MHWs separated by 1 or 2 non-hot days are joined

# For each sea cell, find MHW runs
per_cell_mhw = np.zeros((n_tgt, n_lat, n_lon), dtype=bool)

for lat in range(n_lat):
    for lon in range(n_lon):
        if not sea_cells[lat, lon]:
            continue
        
        hot_series = hot[:, lat, lon]  # (n_tgt,)
        
        # Find runs of hot days
        # We need to join runs separated by 1-2 non-hot days
        # Approach: find all hot days, then identify runs
        # But first join runs separated by 1-2 non-hot days
        
        # Step 1: Identify runs of hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_tgt):
            if hot_series[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, t-1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_tgt-1))
        
        # Step 2: Join runs separated by 1 or 2 non-hot days
        if len(runs) > 1:
            joined_runs = []
            current = list(runs[0])
            for i in range(1, len(runs)):
                gap = runs[i][0] - current[1] - 1
                if gap <= 2:
                    current[1] = runs[i][1]
                else:
                    joined_runs.append(tuple(current))
                    current = list(runs[i])
            joined_runs.append(tuple(current))
            runs = joined_runs
        
        # Step 3: Keep runs of at least 5 days
        for run in runs:
            length = run[1] - run[0] + 1
            if length >= 5:
                per_cell_mhw[run[0]:run[1]+1, lat, lon] = True

print(f"Per-cell MHW cell-days: {per_cell_mhw.sum()}")

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = per_cell_mhw.any(axis=(1, 2))  # (n_tgt,)
print(f"Active days: {active.sum()}")

# Find maximal runs of active days
events = []
in_event = False
for t in range(n_tgt):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t-1))
            in_event = False
if in_event:
    events.append((event_start, n_tgt-1))

print(f"Regional events: {len(events)}")
for onset, end in events:
    print(f"  {tgt_time[onset].date()} to {tgt_time[end].date()}, {end-onset+1} days")

# Save intermediate results
np.save('/tmp/per_cell_mhw.npy', per_cell_mhw)
np.save('/tmp/tgt_data.npy', tgt_data)
np.save('/tmp/sea_cells.npy', sea_cells)
np.save('/tmp/tgt_doy.npy', tgt_doy)
print("Saved intermediate results.")
