
import numpy as np
import datetime
import json
import os

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# Load all cached data
print('Loading cached data...')

# Baseline data
cached = np.load('cache/baseline_data.npz')
baseline_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/baseline_dates.npy')]
sst_data = {}
for d in baseline_dates:
    sst_data[d] = cached[d.strftime('%Y%m%d')]

# Target data
cached_t = np.load('cache/target_data.npz')
target_dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/target_dates.npy')]
target_sst = {}
for d in target_dates:
    target_sst[d] = cached_t[d.strftime('%Y%m%d')]

# Threshold and climatology
threshold_sm = np.load('cache/threshold_smoothed.npy')
clim_sm = np.load('cache/clim_smoothed.npy')

n_lat, n_lon = 60, 60
n_target = len(target_dates)

# Verify sea cells
target_array = np.array([target_sst[d] for d in target_dates], dtype=np.float64)
sea_cells = np.all(np.isfinite(target_array), axis=0)
print(f'Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}')

# Target day-of-year
target_doy = np.array([day_of_year(d) for d in target_dates])

# Compute hot mask
hot = np.zeros((n_lat, n_lon, n_target), dtype=bool)
for t in range(n_target):
    doy = target_doy[t]
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(threshold_sm[doy-1, i, j]):
                hot[i, j, t] = target_array[t, i, j] >= threshold_sm[doy-1, i, j]

# Find per-cell MHWs
mhw_mask = np.zeros((n_lat, n_lon, n_target), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        h = hot[i, j]
        
        # Find runs of hot days
        runs = []
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                runs.append([start, t-1])
            else:
                t += 1
        
        # Keep only runs with >= 5 days
        mhw_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join MHWs separated by 1-2 non-hot days
        if mhw_runs:
            joined = [mhw_runs[0]]
            for k in range(1, len(mhw_runs)):
                gap = mhw_runs[k][0] - joined[-1][1] - 1
                if 1 <= gap <= 2:
                    joined[-1][1] = mhw_runs[k][1]
                else:
                    joined.append(mhw_runs[k])
            
            for r in joined:
                mhw_mask[i, j, r[0]:r[1]+1] = True

print(f'Per-cell MHW mask: {mhw_mask.sum()} cells-day')

# Regional events
active = np.any(mhw_mask, axis=(0, 1))
print(f'Active days: {active.sum()}')

events = []
t = 0
while t < n_target:
    if active[t]:
        start = t
        while t < n_target and active[t]:
            t += 1
        events.append((target_dates[start].isoformat(), target_dates[t-1].isoformat()))
    else:
        t += 1

print(f'Regional events: {len(events)}')
for ev in events:
    print(f'  {ev[0]} to {ev[1]}')
