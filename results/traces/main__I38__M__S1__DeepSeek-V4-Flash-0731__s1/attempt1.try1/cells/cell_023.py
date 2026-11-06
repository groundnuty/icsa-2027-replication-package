
import numpy as np
from datetime import date, timedelta
import json, time

intermediate_dir = 'intermediate'

# Load metadata
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

target_dates = [date.fromisoformat(d) for d in meta['target_dates']]

# Load data
threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
climatology_smooth = np.load(f'{intermediate_dir}/climatology_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

# Day of year mapping
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# Compute doy for each target date
target_doy = [day_of_year(d) for d in target_dates]
print(f"First target date: {target_dates[0]}, doy: {target_doy[0]}")
print(f"Last target date: {target_dates[-1]}, doy: {target_doy[-1]}")

# Get thresholds for target days with CORRECT indexing
# threshold_smooth[doy - 1] for day-of-year doy
n_days = len(target_dates)
target_threshold = np.zeros((n_days, 60, 60))
for i, doy in enumerate(target_doy):
    target_threshold[i] = threshold_smooth[doy - 1]

print(f"target_threshold shape: {target_threshold.shape}")

# Compute hot/cold: SST >= threshold
hot = np.zeros((n_days, 60, 60), dtype=bool)
for i in range(n_days):
    sst = target_sst[i].astype(np.float64)
    th = target_threshold[i]
    hot[i] = (sst >= th) & ~np.isnan(sst)

print(f"Hot days: {hot.sum()}")

# Per-cell MHWs
mhw_mask = np.zeros((n_days, 60, 60), dtype=bool)

t0 = time.time()
for la in range(60):
    for lo in range(60):
        if not sea_cells[la, lo]:
            continue
        
        cell_hot = hot[:, la, lo]
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_days:
            if cell_hot[i]:
                start = i
                while i < n_days and cell_hot[i]:
                    i += 1
                end = i - 1
                runs.append((start, end))
            else:
                i += 1
        
        # Join runs separated by 1-2 cold days
        if runs:
            merged = [runs[0]]
            for r in runs[1:]:
                gap = r[0] - merged[-1][1] - 1
                if gap <= 2:
                    merged[-1] = (merged[-1][0], r[1])
                else:
                    merged.append(r)
            
            # Keep runs of length >= 5
            for start, end in merged:
                length = end - start + 1
                if length >= 5:
                    mhw_mask[start:end+1, la, lo] = True

print(f"MHW computation took {time.time()-t0:.1f}s")
print(f"MHW mask sum: {mhw_mask.sum()}")

np.save(f'{intermediate_dir}/mhw_mask_v2.npy', mhw_mask)
print("MHW mask saved")

# Regional events
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()}")

events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  Event: {target_dates[s]} to {target_dates[e]}")
