
import numpy as np
from datetime import date, timedelta
import json
import os

# ============================================================
# Load all saved intermediate data
# ============================================================
baseline_data = np.load('/tmp/baseline_data.npy')  # (4028, 60, 60)
target_data = np.load('/tmp/target_data.npy')  # (92, 60, 60)
thresh_smooth = np.load('/tmp/thresh_smooth.npy')  # (366, 3600)
clim_smooth = np.load('/tmp/clim_smooth.npy')  # (366, 3600)

print('Loaded all data')

# ============================================================
# Day-of-year function
# ============================================================
month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
def doy(dt):
    return month_starts[dt.month - 1] + dt.day - 1

# Target dates
target_start = date(2008, 6, 1)
target_end = date(2008, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)
n_target = len(target_dates)
print(f'Target dates: {n_target} days')

target_doys = np.array([doy(dt) for dt in target_dates])
print(f'Target day-of-years: {target_doys[0]} to {target_doys[-1]}')

# ============================================================
# Sea cells
# ============================================================
target_flat = target_data.reshape(n_target, -1)  # (92, 3600)
sea_cells = ~np.any(np.isnan(target_flat), axis=0)  # (3600,)
print(f'Sea cells: {sea_cells.sum()} out of 3600')

# ============================================================
# Compute hot days for all cells
# ============================================================
# Thresholds for target days: (92, 3600)
target_thresholds = thresh_smooth[target_doys - 1]  # (92, 3600)

# Hot: SST >= threshold (NaN comparisons give False in numpy)
hot = np.zeros((n_target, 3600), dtype=bool)
for c in range(3600):
    if sea_cells[c]:
        for t in range(n_target):
            sst = target_flat[t, c]
            thr = target_thresholds[t, c]
            if not np.isnan(sst) and not np.isnan(thr):
                hot[t, c] = sst >= thr

print(f'Hot cell-days: {hot.sum()}')

# ============================================================
# Per-cell MHW detection
# ============================================================
mhw_mask_flat = np.zeros((n_target, 3600), dtype=np.uint8)

for c in range(3600):
    if not sea_cells[c]:
        continue
    
    hot_series = hot[:, c].astype(bool)
    
    # Find runs of consecutive hot days
    runs = []
    i = 0
    while i < n_target:
        if hot_series[i]:
            start = i
            while i < n_target and hot_series[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    # Filter runs >= 5 days
    runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    if not runs:
        continue
    
    # Join runs separated by 1 or 2 non-hot days
    joined = []
    current = runs[0]
    for next_run in runs[1:]:
        gap = next_run[0] - current[1] - 1
        if 1 <= gap <= 2:
            current = (current[0], next_run[1])
        else:
            joined.append(current)
            current = next_run
    joined.append(current)
    
    # Mark MHW days
    for start, end in joined:
        mhw_mask_flat[start:end+1, c] = 1

print(f'Cell-days in MHW: {mhw_mask_flat.sum()}')

# ============================================================
# Regional events
# ============================================================
active_days = np.any(mhw_mask_flat > 0, axis=1)  # (92,)
print(f'Active days: {np.where(active_days)[0]}')

events = []
i = 0
while i < n_target:
    if active_days[i]:
        start = i
        while i < n_target and active_days[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

event_list = []
for start, end in events:
    onset = target_dates[start].strftime('%Y-%m-%d')
    end_str = target_dates[end].strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end_str})
    print(f'Regional event: {onset} to {end_str}')

print(f'Total regional events: {len(event_list)}')

# ============================================================
# Prepare output
# ============================================================
os.makedirs('output', exist_ok=True)

# Reshape mask to (92, 60, 60)
mhw_3d = mhw_mask_flat.reshape(n_target, 60, 60)
print(f'MHW mask 3D shape: {mhw_3d.shape}')
print(f'MHW mask dtype: {mhw_3d.dtype}')
print(f'MHW mask unique values: {np.unique(mhw_3d)}')

# Save intermediate for later use
np.save('/tmp/mhw_mask_flat_final.npy', mhw_mask_flat)
print('Saved final mhw_mask_flat')

# ============================================================
# Write report.json
# ============================================================
report = {
    "region": {
        "lat_min": 56.63,
        "lat_max": 57.83,
        "lon_min": 20.23,
        "lon_max": 21.43
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2008-06-01",
        "end": "2008-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print('Written report.json')
print(json.dumps(report, indent=2))
